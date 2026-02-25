"""Invoice processing router - upload, retrieve, update, delete."""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import celery
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import (
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    ProcessingStatus,
)
from app.services.storage import document_exists, upload_document

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=ProcessingStatus, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="Invoice document (PDF, PNG, JPG)")],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    priority: str = Query(default="normal", pattern="^(normal|high)$"),
    callback_url: str | None = None,
) -> ProcessingStatus:
    """Upload an invoice document for OCR processing.

    Accepts PDF, PNG, JPG, TIFF, WEBP formats up to 20MB.
    Returns a processing status with job ID for tracking.
    """
    # Validate file type
    if file.content_type not in [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/webp",
    ]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # Validate file size
    content = await file.read()
    if len(content) > settings.ocr_max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.ocr_max_file_size_mb}MB",
        )

    # 1. Compute content hash and check for duplicates
    document_hash = hashlib.sha256(content).hexdigest()
    existing = await db.execute(
        select(Invoice).where(
            Invoice.organization_id == user.organization_id,
            Invoice.document_hash == document_hash,
        )
    )
    duplicate = existing.scalar_one_or_none()
    if duplicate:
        # Verify the document still exists in S3 (may have been deleted, e.g. MinIO reset)
        file_exists = (
            await asyncio.to_thread(document_exists, duplicate.document_path)
            if duplicate.document_path
            else False
        )
        if file_exists:
            return ProcessingStatus(
                id=duplicate.id,
                status="uploaded",
                progress=0,
                document_id=duplicate.id,
                created_at=duplicate.created_at,
            )
        # Stale record — remove it so we can re-upload
        await db.delete(duplicate)
        await db.flush()

    # 2. Create Invoice record (flush to get id before S3 upload)
    invoice = Invoice(
        organization_id=user.organization_id,
        status="processing",
        document_hash=document_hash,
        document_content_type=file.content_type,
    )
    db.add(invoice)
    await db.flush()

    # 3. Upload to S3/R2 (sync boto3 → thread pool)
    try:
        document_key = await asyncio.to_thread(
            upload_document,
            user.organization_id,
            invoice.id,
            content,
            file.content_type,
            file.filename or "document",
        )
    except Exception as e:
        logger.error("S3 upload failed for invoice %s: %s", invoice.id, e)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload document to storage",
        ) from e

    # 4. Save document path and commit
    invoice.document_path = document_key
    await db.commit()
    await db.refresh(invoice)

    # 5. Queue Celery OCR task (graceful fallback if Redis/Celery is down)
    celery_queued = False
    try:
        celery_app = celery.Celery(broker=settings.celery_broker_url)
        celery_app.send_task(
            "ocr_worker.tasks.process_invoice",
            args=[str(invoice.id), document_key, callback_url, priority],
            queue="ocr",
        )
        celery_queued = True
    except Exception as e:
        logger.warning(
            "Failed to queue OCR task for invoice %s: %s. Invoice saved; manual retry required.",
            invoice.id,
            e,
        )

    # 6. Return processing status
    return ProcessingStatus(
        id=invoice.id,
        status="queued" if celery_queued else "uploaded",
        progress=0,
        estimated_time=30 if priority == "normal" else 15,
        document_id=invoice.id,
        created_at=invoice.created_at,
    )


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/webp",
}
MAX_BATCH_FILES = 50
MAX_BATCH_TOTAL_BYTES = 200 * 1024 * 1024  # 200 MB


async def _process_single_file(
    file_content: bytes,
    content_type: str,
    filename: str,
    db: AsyncSession,
    user: User,
    priority: str,
    callback_url: str | None,
) -> ProcessingStatus:
    """Process a single file within a batch upload.

    Creates an invoice record, uploads to S3, and queues a Celery OCR task.
    Uses a savepoint so failures only roll back this file, not the whole batch.
    """
    # 1. Dedup check
    document_hash = hashlib.sha256(file_content).hexdigest()
    existing = await db.execute(
        select(Invoice).where(
            Invoice.organization_id == user.organization_id,
            Invoice.document_hash == document_hash,
        )
    )
    duplicate = existing.scalar_one_or_none()
    if duplicate:
        file_exists = (
            await asyncio.to_thread(document_exists, duplicate.document_path)
            if duplicate.document_path
            else False
        )
        if file_exists:
            return ProcessingStatus(
                id=duplicate.id,
                status="uploaded",
                progress=0,
                document_id=duplicate.id,
                created_at=duplicate.created_at,
            )
        await db.delete(duplicate)
        await db.flush()

    # 2. Create invoice record inside a savepoint
    async with db.begin_nested():
        invoice = Invoice(
            organization_id=user.organization_id,
            status="processing",
            document_hash=document_hash,
            document_content_type=content_type,
        )
        db.add(invoice)
        await db.flush()

        # 3. Upload to S3
        document_key = await asyncio.to_thread(
            upload_document,
            user.organization_id,
            invoice.id,
            file_content,
            content_type,
            filename,
        )
        invoice.document_path = document_key

    # 4. Queue Celery OCR task (graceful fallback)
    celery_queued = False
    try:
        celery_app = celery.Celery(broker=settings.celery_broker_url)
        celery_app.send_task(
            "ocr_worker.tasks.process_invoice",
            args=[str(invoice.id), document_key, callback_url, priority],
            queue="ocr",
        )
        celery_queued = True
    except Exception as e:
        logger.warning(
            "Failed to queue OCR task for invoice %s: %s",
            invoice.id,
            e,
        )

    return ProcessingStatus(
        id=invoice.id,
        status="queued" if celery_queued else "uploaded",
        progress=0,
        estimated_time=30 if priority == "normal" else 15,
        document_id=invoice.id,
        created_at=invoice.created_at,
    )


@router.post(
    "/upload/batch",
    response_model=list[ProcessingStatus],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_batch(
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    priority: str = Query(default="normal", pattern="^(normal|high)$"),
    callback_url: str | None = None,
) -> list[ProcessingStatus]:
    """Upload multiple invoice documents for batch processing.

    Accepts up to 50 files per batch, 200MB total.
    Each file is processed independently — invalid files are
    reported as failed without blocking valid ones.
    """
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BATCH_FILES} files per batch",
        )

    # Read all file contents and validate total size
    file_data: list[tuple[bytes, str, str]] = []  # (content, content_type, filename)
    total_size = 0
    for f in files:
        content = await f.read()
        total_size += len(content)
        file_data.append((content, f.content_type or "", f.filename or "document"))

    if total_size > MAX_BATCH_TOTAL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total batch size exceeds 200MB",
        )

    # Process each file independently
    results: list[ProcessingStatus] = []
    max_file_bytes = settings.ocr_max_file_size_mb * 1024 * 1024

    for content, content_type, filename in file_data:
        # Validate file type
        if content_type not in ALLOWED_CONTENT_TYPES:
            results.append(
                ProcessingStatus(
                    id=uuid4(),
                    status="failed",
                    progress=0,
                    error_message=f"Unsupported file type: {content_type}",
                    created_at=datetime.now(UTC),
                )
            )
            continue

        # Validate file size
        if len(content) > max_file_bytes:
            results.append(
                ProcessingStatus(
                    id=uuid4(),
                    status="failed",
                    progress=0,
                    error_message=(
                        f"File '{filename}' too large. "
                        f"Maximum size is {settings.ocr_max_file_size_mb}MB"
                    ),
                    created_at=datetime.now(UTC),
                )
            )
            continue

        # Process the file (dedup, S3 upload, Celery queue)
        try:
            result = await _process_single_file(
                content,
                content_type,
                filename,
                db,
                user,
                priority,
                callback_url,
            )
            results.append(result)
        except Exception as e:
            logger.error("Batch file '%s' failed: %s", filename, e)
            results.append(
                ProcessingStatus(
                    id=uuid4(),
                    status="failed",
                    progress=0,
                    error_message=f"Failed to process '{filename}'",
                    created_at=datetime.now(UTC),
                )
            )

    # Commit all successful invoices in one transaction
    await db.commit()

    return results


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID) -> InvoiceResponse:
    """Get invoice details by ID.

    Returns full invoice data including extracted fields,
    confidence scores, and verification status.
    """
    # TODO: Implement get invoice
    # 1. Find invoice by ID
    # 2. Check user has access (same organization)
    # 3. Return full invoice data
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get invoice not yet implemented",
    )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    _user=Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    invoice_status: str | None = Query(default=None, alias="status"),
    date_from: str | None = None,
    date_to: str | None = None,
    seller_pib: str | None = None,
    buyer_pib: str | None = None,
    search: str | None = None,
    sort: str = "created_at",
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> InvoiceListResponse:
    """List invoices with filtering, sorting, and pagination."""
    # TODO: Implement invoice listing
    # 1. Build query with filters
    # 2. Apply sorting
    # 3. Paginate results
    # 4. Return with pagination metadata
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="List invoices not yet implemented",
    )


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(invoice_id: UUID, update_data: InvoiceUpdate) -> InvoiceResponse:
    """Update invoice fields.

    Used for manual corrections after OCR extraction.
    Tracks all changes in audit log.
    """
    # TODO: Implement invoice update
    # 1. Find invoice by ID
    # 2. Check user has edit access
    # 3. Log correction (for ML feedback loop)
    # 4. Update invoice fields
    # 5. Recalculate confidence if needed
    # 6. Return updated invoice
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update invoice not yet implemented",
    )


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(invoice_id: UUID) -> None:
    """Delete invoice and associated document."""
    # TODO: Implement invoice deletion
    # 1. Find invoice by ID
    # 2. Check user has delete access
    # 3. Delete document from S3
    # 4. Delete invoice from database
    # 5. Log deletion
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete invoice not yet implemented",
    )


@router.get("/{invoice_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProcessingStatus:
    """Get current processing status of an invoice.

    Use this to poll for completion after upload.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Map Invoice.status → ProcessingStatus.status + progress
    if invoice.status == "processing":
        if invoice.confidence_score is not None:
            # OCR has started producing results
            proc_status, progress = "processing", 50
        elif invoice.document_path:
            # File saved but OCR hasn't run yet
            proc_status, progress = "uploaded", 0
        else:
            proc_status, progress = "queued", 0
    else:
        status_map: dict[str, tuple[str, int]] = {
            "review": ("completed", 100),
            "verified": ("completed", 100),
            "exported": ("completed", 100),
            "error": ("failed", 0),
        }
        proc_status, progress = status_map.get(invoice.status, ("uploaded", 0))

    return ProcessingStatus(
        id=invoice.id,
        status=proc_status,
        progress=progress,
        error_message=(
            invoice.warnings[0] if invoice.status == "error" and invoice.warnings else None
        ),
        document_id=invoice.id,
        created_at=invoice.created_at,
    )


@router.post("/{invoice_id}/verify")
async def verify_invoice(invoice_id: UUID) -> InvoiceResponse:
    """Mark invoice as verified after human review.

    Sets status to 'verified' and enables export.
    """
    # TODO: Implement verification
    # 1. Find invoice by ID
    # 2. Check all required fields are present
    # 3. Check no blocking warnings
    # 4. Update status to verified
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Verify invoice not yet implemented",
    )
