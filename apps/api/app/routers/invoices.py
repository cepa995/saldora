"""Invoice processing router - upload, retrieve, update, delete."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.config import get_settings
from app.dependencies import get_current_user
from app.schemas.invoice import (
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    ProcessingStatus,
)

router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=ProcessingStatus, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="Invoice document (PDF, PNG, JPG)")],
    priority: str = Query(default="normal", pattern="^(normal|high)$"),
    callback_url: str | None = None,
) -> ProcessingStatus:
    """
    Upload an invoice document for OCR processing.

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
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.ocr_max_file_size_mb}MB",
        )

    # TODO: Implement upload processing
    # 1. Save file to S3/R2
    # 2. Create document record in database
    # 3. Create invoice record with status "processing"
    # 4. Queue OCR task with Celery
    # 5. Return job ID and estimated time

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Upload processing not yet implemented",
    )


@router.post("/upload/batch", response_model=list[ProcessingStatus])
async def upload_batch(
    files: list[UploadFile],
    priority: str = Query(default="normal", pattern="^(normal|high)$"),
) -> list[ProcessingStatus]:
    """
    Upload multiple invoice documents for batch processing.

    Maximum 50 files per batch, 200MB total.
    """
    if len(files) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 files per batch",
        )

    # TODO: Implement batch upload
    # Similar to single upload but processes all files
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Batch upload not yet implemented",
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID) -> InvoiceResponse:
    """
    Get invoice details by ID.

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
    """
    List invoices with filtering, sorting, and pagination.
    """
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
    """
    Update invoice fields.

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
    """
    Delete invoice and associated document.
    """
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
async def get_processing_status(invoice_id: UUID) -> ProcessingStatus:
    """
    Get current processing status of an invoice.

    Use this to poll for completion after upload.
    """
    # TODO: Implement status check
    # 1. Find invoice by ID
    # 2. Return current status and progress
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Processing status not yet implemented",
    )


@router.post("/{invoice_id}/verify")
async def verify_invoice(invoice_id: UUID) -> InvoiceResponse:
    """
    Mark invoice as verified after human review.

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
