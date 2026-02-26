"""Invoice processing router - upload, retrieve, update, delete."""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import celery
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import (
    CompanyInfo,
    FieldConfidence,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    ProcessingStatus,
)
from app.services.storage import (
    delete_document,
    document_exists,
    get_presigned_url,
    upload_document,
)

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


def _build_invoice_response(invoice: Invoice, document_url: str | None = None) -> InvoiceResponse:
    """Convert an Invoice model to an InvoiceResponse schema.

    Handles JSON → Pydantic conversion for nested fields, confidence
    scaling (0–1 in DB → 0–100 in API), and warning message extraction.

    Args:
        invoice: SQLAlchemy Invoice model instance.
        document_url: Optional presigned S3 URL for the document.

    Returns:
        InvoiceResponse ready for serialization.
    """
    # Convert seller/buyer JSON dicts to CompanyInfo
    seller = CompanyInfo(**invoice.seller) if invoice.seller else None
    buyer = CompanyInfo(**invoice.buyer) if invoice.buyer else None

    # Convert field_confidence dict → list[FieldConfidence]
    field_confidences: list[FieldConfidence] = []
    if invoice.field_confidence:
        for item in invoice.field_confidence:
            if isinstance(item, dict):
                field_confidences.append(FieldConfidence(**item))

    # Extract warning messages from structured warnings
    warnings: list[str] = []
    blocked = False
    if invoice.warnings:
        for w in invoice.warnings:
            if isinstance(w, dict):
                warnings.append(w.get("message", str(w)))
                if w.get("severity") == "error":
                    blocked = True
            elif isinstance(w, str):
                warnings.append(w)

    # Scale confidence from 0–1 (DB) to 0–100 (API)
    confidence_score = None
    if invoice.confidence_score is not None:
        confidence_score = round(float(invoice.confidence_score) * 100, 2)

    # Convert line_items JSON → list[dict] (Pydantic handles the rest)
    line_items = invoice.line_items or []

    return InvoiceResponse(
        id=invoice.id,
        status=invoice.status,
        confidence_score=confidence_score,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        seller=seller,
        buyer=buyer,
        subtotal=invoice.subtotal,
        tax_rate=invoice.tax_rate,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        currency=invoice.currency,
        line_items=line_items,
        field_confidences=field_confidences,
        warnings=warnings,
        blocked=blocked,
        document_url=document_url,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


async def _get_invoice_or_404(invoice_id: UUID, db: AsyncSession, user: User) -> Invoice:
    """Fetch an invoice by ID, enforcing multi-tenant isolation.

    Args:
        invoice_id: UUID of the invoice to fetch.
        db: Async database session.
        user: Authenticated user (for organization check).

    Returns:
        Invoice model instance.

    Raises:
        HTTPException: 404 if not found or belongs to another organization.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice or invoice.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Get invoice details by ID.

    Returns full invoice data including extracted fields,
    confidence scores, and verification status.

    Args:
        invoice_id: UUID of the invoice.
        db: Database session.
        user: Authenticated user.

    Returns:
        Full invoice data with presigned document URL.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Generate presigned URL for document download (fail-silent)
    document_url = None
    if invoice.document_path:
        try:
            document_url = await asyncio.to_thread(get_presigned_url, invoice.document_path)
        except Exception:
            logger.warning("Failed to generate presigned URL for invoice %s", invoice_id)

    return _build_invoice_response(invoice, document_url)


ALLOWED_SORT_COLUMNS = {
    "created_at",
    "invoice_date",
    "total_amount",
    "status",
    "confidence_score",
}


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
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
    """List invoices with filtering, sorting, and pagination.

    Args:
        db: Database session.
        user: Authenticated user.
        page: Page number (1-based).
        per_page: Items per page (1–100).
        invoice_status: Filter by status (processing, review, verified, exported, error).
        date_from: Filter invoices on or after this date (YYYY-MM-DD).
        date_to: Filter invoices on or before this date (YYYY-MM-DD).
        seller_pib: Filter by seller's PIB.
        buyer_pib: Filter by buyer's PIB.
        search: Search invoice number, seller name, or buyer name.
        sort: Sort column (created_at, invoice_date, total_amount, status, confidence_score).
        order: Sort direction (asc or desc).

    Returns:
        Paginated list of invoices with metadata.
    """
    from datetime import date as date_type

    # Base filter: multi-tenant isolation
    conditions = [Invoice.organization_id == user.organization_id]

    # Status filter
    if invoice_status:
        conditions.append(Invoice.status == invoice_status)

    # Date range filters
    if date_from:
        try:
            parsed = date_type.fromisoformat(date_from)
            conditions.append(Invoice.invoice_date >= parsed)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_from format. Use YYYY-MM-DD.",
            )

    if date_to:
        try:
            parsed = date_type.fromisoformat(date_to)
            conditions.append(Invoice.invoice_date <= parsed)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date_to format. Use YYYY-MM-DD.",
            )

    # PIB filters (JSON field access)
    if seller_pib:
        conditions.append(Invoice.seller["pib"].as_string() == seller_pib)

    if buyer_pib:
        conditions.append(Invoice.buyer["pib"].as_string() == buyer_pib)

    # Search (ILIKE on invoice_number, seller name, buyer name)
    if search:
        like_pattern = f"%{search}%"
        conditions.append(
            (Invoice.invoice_number.ilike(like_pattern))
            | (Invoice.seller["name"].as_string().ilike(like_pattern))
            | (Invoice.buyer["name"].as_string().ilike(like_pattern))
        )

    # Build base query with all filters
    where_clause = select(Invoice).where(*conditions)

    # Sorting (whitelist to prevent injection)
    if sort not in ALLOWED_SORT_COLUMNS:
        sort = "created_at"
    sort_column = getattr(Invoice, sort)
    order_func = desc if order == "desc" else asc
    where_clause = where_clause.order_by(order_func(sort_column))

    # Get total count
    count_query = select(func.count()).select_from(select(Invoice).where(*conditions).subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * per_page
    paginated_query = where_clause.offset(offset).limit(per_page)

    result = await db.execute(paginated_query)
    invoices = result.scalars().all()

    # Build responses (no presigned URLs in list view — too expensive)
    data = [_build_invoice_response(inv) for inv in invoices]

    return InvoiceListResponse(
        data=data,
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    )


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    update_data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Update invoice fields after OCR extraction.

    Applies partial updates from the request body. Only invoices in
    ``review`` or ``verified`` status can be edited. Editing a verified
    invoice reverts it to ``review``.

    Args:
        invoice_id: UUID of the invoice to update.
        update_data: Partial update payload.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated invoice data.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Only allow edits on review/verified invoices
    if invoice.status not in ("review", "verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit invoice in '{invoice.status}' status",
        )

    updates = update_data.model_dump(exclude_unset=True)
    if not updates:
        return _build_invoice_response(invoice)

    # Direct scalar fields
    direct_fields = {
        "invoice_number",
        "invoice_date",
        "due_date",
        "subtotal",
        "tax_rate",
        "tax_amount",
        "total_amount",
        "currency",
        "line_items",
    }
    for field in direct_fields & updates.keys():
        setattr(invoice, field, updates[field])

    # Seller fields → merge into seller JSON
    seller_updates = {}
    if "seller_pib" in updates:
        seller_updates["pib"] = updates["seller_pib"]
    if "seller_name" in updates:
        seller_updates["name"] = updates["seller_name"]
    if "seller_address" in updates:
        seller_updates["address"] = updates["seller_address"]
    if seller_updates:
        invoice.seller = {**(invoice.seller or {}), **seller_updates}

    # Buyer fields → merge into buyer JSON
    buyer_updates = {}
    if "buyer_pib" in updates:
        buyer_updates["pib"] = updates["buyer_pib"]
    if "buyer_name" in updates:
        buyer_updates["name"] = updates["buyer_name"]
    if "buyer_address" in updates:
        buyer_updates["address"] = updates["buyer_address"]
    if buyer_updates:
        invoice.buyer = {**(invoice.buyer or {}), **buyer_updates}

    # Revert verified → review when fields change
    if invoice.status == "verified":
        invoice.status = "review"

    await db.commit()
    await db.refresh(invoice)

    return _build_invoice_response(invoice)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete an invoice and its associated document from storage.

    Args:
        invoice_id: UUID of the invoice to delete.
        db: Database session.
        user: Authenticated user.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Delete document from S3 (fail-silent — don't block DB deletion)
    if invoice.document_path:
        try:
            await asyncio.to_thread(delete_document, invoice.document_path)
        except Exception:
            logger.warning(
                "Failed to delete S3 document for invoice %s: %s",
                invoice_id,
                invoice.document_path,
            )

    await db.delete(invoice)
    await db.commit()


@router.get("/{invoice_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    invoice_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProcessingStatus:
    """Get current processing status of an invoice.

    Checks Redis for real-time progress from the OCR worker, then
    falls back to database status if no Redis data is available.

    Args:
        invoice_id: The invoice UUID to check.
        request: FastAPI request (provides access to app.state.redis).
        db: Database session.
        user: Authenticated user.

    Returns:
        ProcessingStatus with current stage, progress, and status.
    """
    import json

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Try Redis for real-time progress (best-effort)
    redis_progress = None
    try:
        redis_client = request.app.state.redis
        raw = await redis_client.get(f"invoice:{invoice_id}:progress")
        if raw:
            redis_progress = json.loads(raw)
    except Exception:
        pass

    # If Redis has data and DB status is still "processing", use Redis for live updates
    if redis_progress and invoice.status == "processing":
        stage = redis_progress.get("stage", "")
        progress = redis_progress.get("progress", 0)
        error = redis_progress.get("error")

        if stage == "complete":
            proc_status = "completed"
            progress = 100
            stage = None
        elif stage == "failed":
            proc_status = "failed"
            progress = 0
            stage = None
        else:
            proc_status = "processing"

        return ProcessingStatus(
            id=invoice.id,
            status=proc_status,
            progress=progress,
            stage=stage,
            error_message=error,
            document_id=invoice.id,
            created_at=invoice.created_at,
        )

    # Fall back to DB-based status mapping
    if invoice.status == "processing":
        if invoice.confidence_score is not None:
            proc_status, progress = "processing", 50
        elif invoice.document_path:
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


@router.post("/{invoice_id}/verify", response_model=InvoiceResponse)
async def verify_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Mark invoice as verified after human review.

    Validates that required fields are present and sets the status
    to ``verified``, enabling export.

    Args:
        invoice_id: UUID of the invoice to verify.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated invoice with verified status.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Only review invoices can be verified
    if invoice.status not in ("review",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot verify invoice in '{invoice.status}' status. "
            "Only invoices in 'review' status can be verified.",
        )

    # Check required fields
    missing = []
    if not invoice.invoice_number:
        missing.append("invoice_number")
    if not invoice.invoice_date:
        missing.append("invoice_date")
    if not invoice.seller:
        missing.append("seller")
    if not invoice.total_amount:
        missing.append("total_amount")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields for verification: {', '.join(missing)}",
        )

    invoice.status = "verified"
    await db.commit()
    await db.refresh(invoice)

    return _build_invoice_response(invoice)
