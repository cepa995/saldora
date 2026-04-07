"""Invoice processing router - upload, retrieve, update, delete."""

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated
from uuid import UUID, uuid4

import celery
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import QuotaCheck, check_invoice_quota, get_current_user, require_role
from app.models.accounting_intent import AccountingIntent
from app.models.client import Client
from app.models.correction_log import CorrectionLog
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.accounting_intent import (
    AccountingIntentResponse,
    AccountingIntentReviewRequest,
    AccountingIntentUpdateRequest,
)
from app.schemas.client import ClientSummary
from app.schemas.invoice import (
    BatchPaymentRequest,
    BatchPaymentResponse,
    CompanyInfo,
    FieldConfidence,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    PaymentUpdate,
    ProcessingStatus,
    TaxGroup,
)
from app.services import audit
from app.services.accounting_intent import generate_accounting_intent
from app.services.email import send_invoice_processed_email
from app.services.invoice_verification import check_duplicates, verify_calculations
from app.services.nbs import convert_to_rsd
from app.services.pib import validate_pib
from app.services.storage import (
    delete_document,
    get_presigned_url,
    upload_document,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=ProcessingStatus, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="Invoice document (PDF, PNG, JPG)")],
    request: Request,
    db: AsyncSession = Depends(get_db),
    quota: QuotaCheck = Depends(check_invoice_quota()),
    priority: str = Query(default="normal", pattern="^(normal|high)$"),
    callback_url: str | None = None,
) -> ProcessingStatus:
    """Upload an invoice document for OCR processing.

    Accepts PDF, PNG, JPG, TIFF, WEBP formats up to 20MB.
    Returns a processing status with job ID for tracking.
    """
    user = quota.user

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

    # Validate file size and magic bytes
    content = await file.read()
    if not _validate_magic_bytes(content, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Sadržaj fajla ne odgovara deklarisanom tipu",
        )
    if len(content) > settings.ocr_max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.ocr_max_file_size_mb}MB",
        )

    # Validate image resolution (skip PDFs — they render at fixed DPI)
    if file.content_type and file.content_type.startswith("image/"):
        _check_image_resolution(content, file.filename or "image")

    # 1. Compute content hash (stored for reference, no dedup blocking)
    document_hash = hashlib.sha256(content).hexdigest()

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

    # 4. Save document path, audit, and commit
    invoice.document_path = document_key
    await audit.log(
        db=db,
        action="invoice.create",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invoice",
        entity_id=invoice.id,
        new_values={"document_hash": document_hash, "content_type": file.content_type},
    )
    await db.commit()
    await db.refresh(invoice)

    # Increment usage counter (write-only, survives deletion)
    await _increment_usage(db, user.organization_id, 1)

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

MIN_WIDTH = settings.ocr_min_image_width
MIN_HEIGHT = settings.ocr_min_image_height


def _get_resolution_error(content: bytes, filename: str) -> str | None:
    """Return an error message if image is below minimum resolution, else None.

    Args:
        content: Raw image bytes.
        filename: Original filename (for error message).

    Returns:
        Error string if too small, None if OK.
    """
    from PIL import Image

    try:
        with Image.open(BytesIO(content)) as img:
            w, h = img.size
    except Exception:
        return f"Cannot read image '{filename}'"

    if w < MIN_WIDTH or h < MIN_HEIGHT:
        return f"Rezolucija slike je premala ({w}x{h}px). Minimum je {MIN_WIDTH}x{MIN_HEIGHT}px."
    return None


_MAGIC_BYTES = {
    "application/pdf": [b"%PDF"],
    "image/png": [b"\x89PNG"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/tiff": [b"II\x2a\x00", b"MM\x00\x2a"],
    "image/webp": [b"RIFF"],
}


def _validate_magic_bytes(content: bytes, content_type: str | None) -> bool:
    """Validate file content matches declared MIME type via magic bytes.

    Args:
        content: Raw file bytes.
        content_type: Declared MIME type from upload header.

    Returns:
        True if magic bytes match the declared type.
    """
    if not content_type or content_type not in _MAGIC_BYTES:
        return True  # Unknown type — let other validation handle it
    signatures = _MAGIC_BYTES[content_type]
    return any(content[: len(sig)] == sig for sig in signatures)


def _check_image_resolution(content: bytes, filename: str) -> None:
    """Raise HTTPException if image is below minimum resolution.

    Args:
        content: Raw image bytes.
        filename: Original filename (for error message).
    """
    error = _get_resolution_error(content, filename)
    if error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )


async def _process_single_file(
    file_content: bytes,
    content_type: str,
    filename: str,
    db: AsyncSession,
    user: User,
    priority: str,
    callback_url: str | None,
    countdown: int = 0,
) -> ProcessingStatus:
    """Process a single file within a batch upload.

    Creates an invoice record, uploads to S3, and queues a Celery OCR task.
    Uses a savepoint so failures only roll back this file, not the whole batch.

    Args:
        countdown: Seconds to delay task dispatch (for staggering batches).
    """
    # 1. Compute content hash (stored for reference, no dedup blocking)
    document_hash = hashlib.sha256(file_content).hexdigest()

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
        celery_kwargs: dict = {"queue": "ocr"}
        if countdown > 0:
            celery_kwargs["countdown"] = countdown
        celery_app.send_task(
            "ocr_worker.tasks.process_invoice",
            args=[str(invoice.id), document_key, callback_url, priority],
            **celery_kwargs,
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
    quota: QuotaCheck = Depends(check_invoice_quota()),
    priority: str = Query(default="normal", pattern="^(normal|high)$"),
    callback_url: str | None = None,
) -> list[ProcessingStatus]:
    """Upload multiple invoice documents for batch processing.

    Accepts up to 50 files per batch, 200MB total.
    Each file is processed independently — invalid files are
    reported as failed without blocking valid ones.
    """
    user = quota.user

    # Check batch fits within remaining quota
    if quota.invoice_limit is not None and quota.monthly_usage + len(files) > quota.invoice_limit:
        from app.dependencies import _next_plan_tier

        remaining = max(0, quota.invoice_limit - quota.monthly_usage)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "detail": (
                    f"Možete otpremiti još {remaining} faktura ovog meseca "
                    f"({quota.plan_name} plan: {quota.invoice_limit} mesečno). "
                    f"Nadogradite plan za nastavak."
                ),
                "code": "invoice_limit_exceeded",
                "plan": quota.plan_name,
                "limit": quota.invoice_limit,
                "usage": quota.monthly_usage,
                "required_plan": _next_plan_tier(quota.plan_name),
            },
        )
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

    for batch_idx, (content, content_type, filename) in enumerate(file_data):
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

        # Validate image resolution
        if content_type.startswith("image/"):
            error = _get_resolution_error(content, filename)
            if error:
                results.append(
                    ProcessingStatus(
                        id=uuid4(),
                        status="failed",
                        progress=0,
                        error_message=error,
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
                countdown=batch_idx * 1,  # Stagger: 0s, 1s, 2s, ...
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

    # Increment usage record (never decremented — survives invoice deletion)
    success_count = sum(1 for r in results if r.status == "processing")
    if success_count > 0:
        await _increment_usage(db, user.organization_id, success_count)

    return results


async def _increment_usage(
    db: AsyncSession,
    organization_id: UUID,
    count: int,
) -> None:
    """Increment monthly usage counter (write-only, never decremented).

    Creates a usage_records row for the current month if it doesn't exist,
    then increments invoices_count. This counter persists even if invoices
    are deleted, preventing billing exploits.

    Args:
        db: Database session.
        organization_id: Organization to increment for.
        count: Number of invoices to add.
    """
    from app.models.usage_record import UsageRecord

    now = datetime.now(UTC)
    period_start = now.replace(day=1).date()
    if now.month == 12:
        period_end = now.replace(year=now.year + 1, month=1, day=1).date()
    else:
        period_end = now.replace(month=now.month + 1, day=1).date()

    result = await db.execute(
        select(UsageRecord).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.period_start == period_start,
        )
    )
    record = result.scalar_one_or_none()

    if record:
        record.invoices_count += count
    else:
        record = UsageRecord(
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end,
            invoices_count=count,
        )
        db.add(record)

    await db.commit()


def _json_safe(obj):
    """Recursively convert Decimal/date/datetime to str for JSON column storage."""
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(i) for i in obj]
    return obj


async def _update_exchange_rate(
    invoice: Invoice,
    request: Request,
    db: AsyncSession,
) -> None:
    """Compute and store RSD equivalent for a non-RSD invoice.

    Sets exchange_rate, exchange_rate_date, and total_amount_rsd on the
    invoice model. No-op for RSD invoices.

    Args:
        invoice: Invoice model with currency and total_amount set.
        request: FastAPI request (for Redis access).
        db: Database session.
    """
    if invoice.currency == "RSD" or not invoice.total_amount:
        invoice.exchange_rate = None
        invoice.exchange_rate_date = None
        invoice.total_amount_rsd = None
        return

    redis = request.app.state.redis
    invoice_date = invoice.invoice_date or datetime.now(UTC).date()

    result = await convert_to_rsd(db, redis, invoice.total_amount, invoice.currency, invoice_date)

    if result.get("error"):
        logger.warning(
            "Exchange rate conversion failed for invoice %s: %s",
            invoice.id,
            result["error"],
        )
        return

    invoice.exchange_rate = result["exchange_rate"]
    invoice.exchange_rate_date = result["rate_date"]
    invoice.total_amount_rsd = result["rsd_amount"]


def _build_invoice_response(
    invoice: Invoice,
    document_url: str | None = None,
    accounting_review_needed: bool | None = None,
    pdv_book_type: str | None = None,
    client_summary: ClientSummary | None = None,
) -> InvoiceResponse:
    """Convert an Invoice model to an InvoiceResponse schema.

    Handles JSON → Pydantic conversion for nested fields, confidence
    scaling (0–1 in DB → 0–100 in API), and warning message extraction.

    Args:
        invoice: SQLAlchemy Invoice model instance.
        document_url: Optional presigned S3 URL for the document.
        accounting_review_needed: Whether the accounting intent needs review.
        pdv_book_type: PDV book type (KPR/KIR) from accounting intent.

    Returns:
        InvoiceResponse ready for serialization.
    """
    # Convert seller/buyer JSON dicts to CompanyInfo.
    # OCR may produce dicts with all-null values; treat those as absent.
    seller = None
    if invoice.seller and any(v is not None for v in invoice.seller.values()):
        seller = CompanyInfo(**invoice.seller)
    buyer = None
    if invoice.buyer and any(v is not None for v in invoice.buyer.values()):
        buyer = CompanyInfo(**invoice.buyer)

    # Convert field_confidence dict → list[FieldConfidence]
    # Scale confidence from 0–1 (DB) to 0–100 (API), same as overall score
    field_confidences: list[FieldConfidence] = []
    if invoice.field_confidence:
        for item in invoice.field_confidence:
            if isinstance(item, dict):
                scaled = dict(item)
                raw = scaled.get("confidence", 0)
                scaled["confidence"] = round(float(raw) * 100, 2) if raw is not None else 0
                field_confidences.append(FieldConfidence(**scaled))

    # Extract warning messages and per-field severity from structured warnings
    warnings: list[str] = []
    blocked = False
    field_warnings: dict[str, str] = {}
    if invoice.warnings:
        for w in invoice.warnings:
            if isinstance(w, dict):
                warnings.append(w.get("message", str(w)))
                severity = w.get("severity", "warning")
                if severity == "error":
                    blocked = True
                # Track highest severity per field for UI highlighting
                fn = w.get("field_name")
                if fn:
                    if fn not in field_warnings or severity == "error":
                        field_warnings[fn] = severity
            elif isinstance(w, str):
                warnings.append(w)

    # Scale confidence from 0–1 (DB) to 0–100 (API)
    confidence_score = None
    if invoice.confidence_score is not None:
        confidence_score = round(float(invoice.confidence_score) * 100, 2)

    # Convert line_items JSON → list[dict] (Pydantic handles the rest)
    line_items = invoice.line_items or []

    # Convert tax_groups JSON → list[TaxGroup]
    tax_groups: list[TaxGroup] = []
    if invoice.tax_groups:
        for tg in invoice.tax_groups:
            if isinstance(tg, dict):
                tax_groups.append(TaxGroup(**tg))

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
        exchange_rate=invoice.exchange_rate,
        exchange_rate_date=invoice.exchange_rate_date,
        total_amount_rsd=invoice.total_amount_rsd,
        line_items=line_items,
        tax_groups=tax_groups,
        field_confidences=field_confidences,
        warnings=warnings,
        blocked=blocked,
        field_warnings=field_warnings,
        accounting_review_needed=accounting_review_needed,
        pdv_book_type=pdv_book_type,
        payment_status=invoice.payment_status or "unpaid",
        paid_amount=invoice.paid_amount,
        paid_date=invoice.paid_date,
        payment_notes=invoice.payment_notes,
        client_id=invoice.client_id,
        client=client_summary,
        document_url=document_url,
        raw_ocr_text=invoice.raw_ocr_text,
        raw_llm_output=invoice.raw_llm_output,
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Get invoice details by ID.

    Returns full invoice data including extracted fields,
    confidence scores, and verification status.

    Args:
        invoice_id: UUID of the invoice.
        request: FastAPI request (for Redis access).
        db: Database session.
        user: Authenticated user.

    Returns:
        Full invoice data with presigned document URL.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Lazy-compute exchange rate for non-RSD invoices after OCR processing
    if invoice.currency != "RSD" and invoice.total_amount and invoice.exchange_rate is None:
        await _update_exchange_rate(invoice, request, db)
        await db.commit()
        await db.refresh(invoice)

    # Generate presigned URL for document download (fail-silent)
    document_url = None
    if invoice.document_path:
        try:
            document_url = await asyncio.to_thread(get_presigned_url, invoice.document_path)
        except Exception:
            logger.warning("Failed to generate presigned URL for invoice %s", invoice_id)

    # Load client summary if assigned
    client_summary = None
    if invoice.client_id:
        client_result = await db.execute(select(Client).where(Client.id == invoice.client_id))
        client = client_result.scalar_one_or_none()
        if client:
            client_summary = ClientSummary(id=client.id, name=client.name, pib=client.pib)

    return _build_invoice_response(invoice, document_url, client_summary=client_summary)


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
    accounting_review: bool | None = Query(default=None),
    book_type: str | None = Query(default=None, pattern="^(KPR|KIR)$"),
    client_id: UUID | None = Query(default=None, description="Filter by client ID"),
    payment_status: str | None = Query(default=None, description="Filter by payment status"),
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
        accounting_review: Filter by accounting review status (true = needs review).
        book_type: Filter by PDV book type (KPR or KIR).
        client_id: Filter by assigned client (Agency feature).

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

    # Accounting review filter (subquery on accounting_intents)
    if accounting_review is True:
        conditions.append(
            Invoice.id.in_(
                select(AccountingIntent.invoice_id).where(
                    AccountingIntent.requires_review.is_(True)
                )
            )
        )
    elif accounting_review is False:
        conditions.append(
            ~Invoice.id.in_(
                select(AccountingIntent.invoice_id).where(
                    AccountingIntent.requires_review.is_(True)
                )
            )
        )

    # PDV book type filter (subquery on accounting_intents JSONB)
    if book_type:
        conditions.append(
            Invoice.id.in_(
                select(AccountingIntent.invoice_id).where(
                    AccountingIntent.pdv_book_entries["book_type"].as_string() == book_type
                )
            )
        )

    # Client filter (Agency feature)
    if client_id:
        conditions.append(Invoice.client_id == client_id)

    # Payment status filter
    if payment_status:
        valid_payment_statuses = {"unpaid", "partially_paid", "paid"}
        if payment_status not in valid_payment_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment_status. Must be one of: "
                f"{', '.join(valid_payment_statuses)}",
            )
        conditions.append(Invoice.payment_status == payment_status)

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

    # Batch-load accounting review flags and book types for the returned invoices
    review_map: dict[str, bool] = {}
    book_type_map: dict[str, str | None] = {}
    client_map: dict[str, ClientSummary] = {}
    if invoices:
        invoice_ids = [inv.id for inv in invoices]
        intent_result = await db.execute(
            select(
                AccountingIntent.invoice_id,
                AccountingIntent.requires_review,
                AccountingIntent.pdv_book_entries["book_type"].as_string().label("book_type"),
            ).where(AccountingIntent.invoice_id.in_(invoice_ids))
        )
        for row in intent_result:
            inv_id = str(row.invoice_id)
            review_map[inv_id] = row.requires_review
            book_type_map[inv_id] = row.book_type

        # Batch-load client summaries for invoices with client_id
        distinct_client_ids = {inv.client_id for inv in invoices if inv.client_id}
        if distinct_client_ids:
            client_result = await db.execute(
                select(Client).where(Client.id.in_(distinct_client_ids))
            )
            for c in client_result.scalars():
                client_map[str(c.id)] = ClientSummary(id=c.id, name=c.name, pib=c.pib)

    # Build responses (no presigned URLs in list view — too expensive)
    data = [
        _build_invoice_response(
            inv,
            accounting_review_needed=review_map.get(str(inv.id)),
            pdv_book_type=book_type_map.get(str(inv.id)),
            client_summary=client_map.get(str(inv.client_id)) if inv.client_id else None,
        )
        for inv in invoices
    ]

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
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> InvoiceResponse:
    """Update invoice fields after OCR extraction.

    Applies partial updates from the request body. Only invoices in
    ``review`` or ``verified`` status can be edited. Editing a verified
    invoice reverts it to ``review``.

    Args:
        invoice_id: UUID of the invoice to update.
        update_data: Partial update payload.
        request: HTTP request for audit context.
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

    # Snapshot old values for audit trail
    old_values = {k: _json_safe(getattr(invoice, k, None)) for k in updates if hasattr(invoice, k)}

    # Generate presigned URL so the document stays visible in the response
    document_url = None
    if invoice.document_path:
        try:
            document_url = await asyncio.to_thread(get_presigned_url, invoice.document_path)
        except Exception:
            logger.warning("Failed to generate presigned URL for invoice %s", invoice_id)

    if not updates:
        return _build_invoice_response(invoice, document_url)

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
        "tax_groups",
    }

    # JSON columns need Decimal→str conversion for serialization
    json_columns = {"line_items", "tax_groups"}
    for field in direct_fields & updates.keys():
        value = updates[field]
        if field in json_columns and isinstance(value, list):
            value = _json_safe(value)
        setattr(invoice, field, value)

    # Seller fields → merge into seller JSON
    seller_updates = {}
    for key, json_key in [
        ("seller_pib", "pib"),
        ("seller_mb", "mb"),
        ("seller_name", "name"),
        ("seller_address", "address"),
        ("seller_city", "city"),
        ("seller_postal_code", "postal_code"),
    ]:
        if key in updates:
            seller_updates[json_key] = updates[key]
    if seller_updates:
        invoice.seller = {**(invoice.seller or {}), **seller_updates}

    # Buyer fields → merge into buyer JSON
    buyer_updates = {}
    for key, json_key in [
        ("buyer_pib", "pib"),
        ("buyer_mb", "mb"),
        ("buyer_name", "name"),
        ("buyer_address", "address"),
        ("buyer_city", "city"),
        ("buyer_postal_code", "postal_code"),
    ]:
        if key in updates:
            buyer_updates[json_key] = updates[key]
    if buyer_updates:
        invoice.buyer = {**(invoice.buyer or {}), **buyer_updates}

    # Revert verified → review when fields change
    if invoice.status == "verified":
        invoice.status = "review"

    # Log corrections for each changed field (quality monitoring)
    confidence_map: dict[str, float | None] = {}
    if invoice.field_confidence:
        for item in invoice.field_confidence:
            if isinstance(item, dict):
                confidence_map[item["field_name"]] = item.get("confidence")

    for field_name, old_val in old_values.items():
        new_val = updates.get(field_name)
        if str(old_val) != str(new_val):
            db.add(
                CorrectionLog(
                    invoice_id=invoice.id,
                    organization_id=user.organization_id,
                    user_id=user.id,
                    field_name=field_name,
                    original_value=str(old_val) if old_val is not None else None,
                    corrected_value=str(new_val),
                    model_confidence=confidence_map.get(field_name),
                )
            )

    # Recalculate RSD equivalent if currency or total changed
    currency_changed = "currency" in updates
    amount_changed = "total_amount" in updates
    if (currency_changed or amount_changed) and invoice.total_amount and invoice.currency:
        await _update_exchange_rate(invoice, request, db)

    # Audit the update (same transaction)
    await audit.log(
        db=db,
        action="invoice.update",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invoice",
        entity_id=invoice.id,
        old_values=_json_safe(old_values),
        new_values=_json_safe(updates),
    )

    # Sync denormalized line items if relevant fields changed
    _sync_fields = {"line_items", "seller", "invoice_date", "currency"}
    if _sync_fields & set(updates.keys()):
        try:
            from app.services.line_item_sync import sync_line_items_orm

            await sync_line_items_orm(db, invoice)
        except Exception:
            pass  # Non-blocking — logged inside sync function

    await db.commit()
    await db.refresh(invoice)

    return _build_invoice_response(invoice, document_url)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> None:
    """Delete an invoice and its associated document from storage.

    Args:
        invoice_id: UUID of the invoice to delete.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Snapshot key fields for audit trail before deletion
    old_values = {
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "total_amount": _json_safe(invoice.total_amount),
    }

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

    # Audit the deletion (same transaction as the DELETE)
    await audit.log(
        db=db,
        action="invoice.delete",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invoice",
        entity_id=invoice.id,
        old_values=old_values,
    )

    # Delete related records that don't have ON DELETE CASCADE
    from sqlalchemy import delete as sa_delete

    from app.models.correction_log import CorrectionLog
    from app.models.line_item import InvoiceLineItem

    await db.execute(sa_delete(CorrectionLog).where(CorrectionLog.invoice_id == invoice.id))
    await db.execute(sa_delete(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id))

    await db.delete(invoice)
    await db.commit()


@router.get("/queue/info")
async def get_queue_info(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get queue information for the current organization.

    Returns the number of invoices currently in the processing queue
    and an estimated wait time based on processing speed.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        Queue position and estimated wait time.
    """
    # Count all processing invoices globally (queue depth)
    global_result = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.status == "processing")
    )
    global_queue = global_result.scalar() or 0

    # Count this org's processing invoices
    org_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.status == "processing",
            Invoice.organization_id == user.organization_id,
        )
    )
    org_queue = org_result.scalar() or 0

    # Estimate: 4 concurrent workers × ~5s per invoice = ~48 invoices/min
    invoices_per_minute = 48
    estimated_minutes = max(1, round(global_queue / invoices_per_minute))

    return {
        "queue_depth": global_queue,
        "your_pending": org_queue,
        "estimated_minutes": estimated_minutes,
        "workers": 4,
    }


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
    request: Request,
    background_tasks: BackgroundTasks,
    force: bool = Query(default=False, description="Force verify even if duplicate (admin only)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> InvoiceResponse:
    """Mark invoice as verified after human review.

    Validates that required fields are present and sets the status
    to ``verified``, enabling export.

    Args:
        invoice_id: UUID of the invoice to verify.
        request: HTTP request for audit context.
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
    field_labels = {
        "invoice_number": "Broj fakture",
        "invoice_date": "Datum fakture",
        "seller": "Podaci o prodavcu",
        "total_amount": "Ukupan iznos",
    }
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
        labels = ", ".join(field_labels.get(f, f) for f in missing)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nedostaju obavezna polja za verifikaciju: {labels}",
        )

    # Run verification checks (warnings, non-blocking)
    verification_warnings: list[dict] = []

    # PIB format validation
    if invoice.seller and isinstance(invoice.seller, dict) and invoice.seller.get("pib"):
        valid, err = validate_pib(invoice.seller["pib"])
        if not valid:
            verification_warnings.append(
                {
                    "message": f"PIB prodavca: {err}",
                    "severity": "warning",
                    "field_name": "seller_pib",
                }
            )
    if invoice.buyer and isinstance(invoice.buyer, dict) and invoice.buyer.get("pib"):
        valid, err = validate_pib(invoice.buyer["pib"])
        if not valid:
            verification_warnings.append(
                {
                    "message": f"PIB kupca: {err}",
                    "severity": "warning",
                    "field_name": "buyer_pib",
                }
            )

    # Mathematical verification
    verification_warnings.extend(verify_calculations(invoice))

    # Duplicate detection — blocks verification unless force=True (admin only)
    dup_warning = await check_duplicates(db, invoice, user.organization_id)
    if dup_warning:
        if force and user.role == "admin":
            verification_warnings.append(
                {**dup_warning, "message": dup_warning["message"] + " (admin override)"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=dup_warning["message"]
                + ". Kontaktirajte administratora za ručno odobrenje.",
            )

    # Replace verification warnings (not append — prevents duplicates on re-verify)
    invoice.warnings = verification_warnings

    # Generate accounting intent (non-blocking).
    # Uses a savepoint so a failure here does not poison the parent transaction.
    try:
        async with db.begin_nested():
            await generate_accounting_intent(db, invoice, user.organization_id)
    except Exception:
        logger.exception("Failed to generate AccountingIntent for invoice %s", invoice.id)

    # Sync denormalized line items for reports
    try:
        from app.services.line_item_sync import sync_line_items_orm

        await sync_line_items_orm(db, invoice)
    except Exception:
        logger.exception("Failed to sync line items for invoice %s", invoice.id)

    old_status = invoice.status
    invoice.status = "verified"

    # Audit the verification (same transaction)
    await audit.log(
        db=db,
        action="invoice.verify",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invoice",
        entity_id=invoice.id,
        old_values={"status": old_status},
        new_values={"status": "verified"},
    )

    await db.commit()
    await db.refresh(invoice)

    # Notify the user who uploaded the invoice
    background_tasks.add_task(
        send_invoice_processed_email,
        user.email,
        user.first_name,
        invoice.invoice_number or str(invoice.id)[:8],
        str(invoice.id),
    )

    # Generate presigned URL so the document stays visible in the response
    document_url = None
    if invoice.document_path:
        try:
            document_url = await asyncio.to_thread(get_presigned_url, invoice.document_path)
        except Exception:
            logger.warning("Failed to generate presigned URL for invoice %s", invoice_id)

    return _build_invoice_response(invoice, document_url)


@router.get("/{invoice_id}/accounting-intent", response_model=AccountingIntentResponse)
async def get_accounting_intent(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountingIntentResponse:
    """Get the accounting intent for an invoice.

    Returns the accounting classification, VAT treatment, suggested konta,
    and review flags generated during verification.

    Args:
        invoice_id: UUID of the invoice.
        db: Database session.
        user: Authenticated user.

    Returns:
        AccountingIntentResponse with classification details.
    """
    # Verify invoice belongs to user's organization
    await _get_invoice_or_404(invoice_id, db, user)

    result = await db.execute(
        select(AccountingIntent).where(
            AccountingIntent.invoice_id == invoice_id,
            AccountingIntent.organization_id == user.organization_id,
        )
    )
    intent = result.scalar_one_or_none()

    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accounting intent not found. Invoice must be verified first.",
        )

    return AccountingIntentResponse.model_validate(intent)


@router.patch("/{invoice_id}/accounting-intent", response_model=AccountingIntentResponse)
async def update_accounting_intent(
    invoice_id: UUID,
    body: AccountingIntentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountingIntentResponse:
    """Update accounting intent fields (konta, classification, notes).

    Args:
        invoice_id: UUID of the invoice.
        body: Fields to update.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated AccountingIntentResponse.
    """
    await _get_invoice_or_404(invoice_id, db, user)

    result = await db.execute(
        select(AccountingIntent).where(
            AccountingIntent.invoice_id == invoice_id,
            AccountingIntent.organization_id == user.organization_id,
        )
    )
    intent = result.scalar_one_or_none()

    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accounting intent not found. Invoice must be verified first.",
        )

    update_data = body.model_dump(exclude_unset=True)
    if "suggested_konta" in update_data:
        update_data["suggested_konta"] = body.suggested_konta.model_dump()

    for field, value in update_data.items():
        setattr(intent, field, value)

    await db.commit()
    await db.refresh(intent)

    return AccountingIntentResponse.model_validate(intent)


@router.post("/{invoice_id}/accounting-intent/review", response_model=AccountingIntentResponse)
async def review_accounting_intent(
    invoice_id: UUID,
    body: AccountingIntentReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> AccountingIntentResponse:
    """Mark an accounting intent as reviewed.

    Sets reviewed_by to the current user and reviewed_at to now.
    Clears the requires_review flag.

    Args:
        invoice_id: UUID of the invoice.
        body: Optional notes from the reviewer.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated AccountingIntentResponse.
    """
    await _get_invoice_or_404(invoice_id, db, user)

    result = await db.execute(
        select(AccountingIntent).where(
            AccountingIntent.invoice_id == invoice_id,
            AccountingIntent.organization_id == user.organization_id,
        )
    )
    intent = result.scalar_one_or_none()

    if not intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accounting intent not found. Invoice must be verified first.",
        )

    intent.requires_review = False
    intent.reviewed_by = user.id
    intent.reviewed_at = datetime.now(UTC)
    if body.notes is not None:
        intent.notes = body.notes

    await db.commit()
    await db.refresh(intent)

    return AccountingIntentResponse.model_validate(intent)


@router.patch("/{invoice_id}/client", response_model=InvoiceResponse)
async def assign_client(
    invoice_id: UUID,
    request: Request,
    client_id: UUID | None = Query(description="Client ID to assign, or null to unassign"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> InvoiceResponse:
    """Assign or unassign a client to an invoice.

    Args:
        invoice_id: UUID of the invoice.
        request: HTTP request for audit context.
        client_id: Client UUID to assign, or None to unassign.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated invoice with client summary.
    """
    invoice = await _get_invoice_or_404(invoice_id, db, user)

    client_summary = None
    if client_id is not None:
        # Validate client belongs to same organization
        result = await db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
        client = result.scalar_one_or_none()
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Klijent nije pronađen",
            )
        client_summary = ClientSummary(id=client.id, name=client.name, pib=client.pib)

    old_client_id = invoice.client_id
    invoice.client_id = client_id

    await audit.log(
        db=db,
        action="invoice.assign_client",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invoice",
        entity_id=invoice.id,
        old_values={"client_id": str(old_client_id) if old_client_id else None},
        new_values={"client_id": str(client_id) if client_id else None},
    )

    await db.commit()
    await db.refresh(invoice)

    # Generate presigned URL
    document_url = None
    if invoice.document_path:
        try:
            document_url = await asyncio.to_thread(get_presigned_url, invoice.document_path)
        except Exception:
            logger.warning("Failed to generate presigned URL for invoice %s", invoice_id)

    return _build_invoice_response(invoice, document_url, client_summary=client_summary)


# ---------------------------------------------------------------------------
# Payment tracking
# ---------------------------------------------------------------------------


@router.patch("/{invoice_id}/payment", response_model=InvoiceResponse)
async def record_payment(
    invoice_id: UUID,
    body: PaymentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> InvoiceResponse:
    """Record a payment against an invoice.

    Adds the payment amount to the existing paid_amount. Automatically
    sets payment_status based on how much has been paid relative to
    total_amount.

    Args:
        invoice_id: UUID of the invoice to record payment for.
        body: Payment details (amount, date, notes).
        request: HTTP request for audit logging.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated invoice response.
    """
    from datetime import date as date_type
    from decimal import Decimal

    invoice = await _get_invoice_or_404(invoice_id, db, user)

    # Only allow payment on verified or exported invoices
    if invoice.status not in ("verified", "exported"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uplata se može evidentirati samo za verifikovane ili izvezene fakture",
        )

    if invoice.total_amount is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Faktura nema ukupan iznos",
        )

    # Calculate new paid_amount
    current_paid = invoice.paid_amount or Decimal("0")
    new_paid = current_paid + body.amount

    if new_paid > invoice.total_amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ukupan plaćeni iznos ({new_paid}) premašuje "
            f"iznos fakture ({invoice.total_amount})",
        )

    # Update payment fields
    old_status = invoice.payment_status
    old_amount = invoice.paid_amount

    invoice.paid_amount = new_paid
    invoice.paid_date = body.payment_date or date_type.today()
    if body.notes:
        existing_notes = invoice.payment_notes or ""
        if existing_notes:
            invoice.payment_notes = f"{existing_notes}\n{body.notes}"
        else:
            invoice.payment_notes = body.notes

    # Auto-set payment_status
    if new_paid >= invoice.total_amount:
        invoice.payment_status = "paid"
    elif new_paid > 0:
        invoice.payment_status = "partially_paid"
    else:
        invoice.payment_status = "unpaid"

    await audit.log(
        db=db,
        action="invoice.record_payment",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invoice",
        entity_id=invoice.id,
        old_values={
            "payment_status": old_status,
            "paid_amount": str(old_amount) if old_amount else None,
        },
        new_values={
            "payment_status": invoice.payment_status,
            "paid_amount": str(invoice.paid_amount),
            "paid_date": str(invoice.paid_date),
        },
    )

    await db.commit()
    await db.refresh(invoice)

    document_url = None
    if invoice.document_path:
        try:
            document_url = await asyncio.to_thread(get_presigned_url, invoice.document_path)
        except Exception:
            logger.warning("Failed to generate presigned URL for invoice %s", invoice_id)

    return _build_invoice_response(invoice, document_url)


@router.post("/batch-payment", response_model=BatchPaymentResponse)
async def batch_mark_as_paid(
    body: BatchPaymentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> BatchPaymentResponse:
    """Mark multiple invoices as fully paid.

    Sets payment_status='paid', paid_amount=total_amount, paid_date=today
    for each invoice. Skips invoices that aren't verified/exported.

    Args:
        body: List of invoice IDs to mark as paid.
        request: HTTP request for audit logging.
        db: Database session.
        user: Authenticated user.

    Returns:
        Summary of updated and skipped invoices.
    """
    from datetime import date as date_type

    result = await db.execute(
        select(Invoice).where(
            Invoice.id.in_(body.invoice_ids),
            Invoice.organization_id == user.organization_id,
        )
    )
    invoices = list(result.scalars().all())

    updated = 0
    skipped_ids: list[UUID] = []
    today = date_type.today()

    for inv in invoices:
        if inv.status not in ("verified", "exported") or inv.total_amount is None:
            skipped_ids.append(inv.id)
            continue

        old_status = inv.payment_status
        inv.payment_status = "paid"
        inv.paid_amount = inv.total_amount
        inv.paid_date = today
        updated += 1

        await audit.log(
            db=db,
            action="invoice.batch_payment",
            request=request,
            organization_id=user.organization_id,
            user_id=user.id,
            entity_type="invoice",
            entity_id=inv.id,
            old_values={"payment_status": old_status},
            new_values={"payment_status": "paid", "paid_amount": str(inv.total_amount)},
        )

    # IDs that weren't found in this org
    found_ids = {inv.id for inv in invoices}
    for req_id in body.invoice_ids:
        if req_id not in found_ids:
            skipped_ids.append(req_id)

    await db.commit()

    return BatchPaymentResponse(
        updated=updated,
        skipped=len(skipped_ids),
        skipped_ids=skipped_ids,
    )
