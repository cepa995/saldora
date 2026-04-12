"""Export router - generate exports in various formats."""

import json
import logging
import re
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_feature, require_role
from app.models.export_template import ExportTemplate
from app.models.invoice import Invoice
from app.models.minimax_config import MiniMaxConfig
from app.models.scheduled_export_log import ScheduledExportLog
from app.plans import Feature
from app.schemas.export import (
    AuditExportRequest,
    AuditExportResponse,
    ExportBlockedResponse,
    ExportRequest,
    ExportTemplateCreate,
    ExportTemplateResponse,
    ExportTemplateUpdate,
)
from app.schemas.minimax import (
    MiniMaxConfigCreate,
    MiniMaxConfigResponse,
    MiniMaxConfigUpdate,
    MiniMaxPushRequest,
    MiniMaxPushResponse,
    MiniMaxPushResult,
)
from app.schemas.pdv_books import PdvBookPreviewResponse, PdvBookRequest
from app.services.export.audit import AUDIT_URL_EXPIRY, generate_audit_export
from app.services.export.core import (
    VALID_FIELD_KEYS,
    check_export_blocking,
    load_invoices_for_export,
)
from app.services.export.csv_gen import generate_csv
from app.services.export.json_gen import generate_json
from app.services.export.minimax_xml import generate_minimax_xml
from app.services.export.pdv_books import (
    fetch_pdv_book_entries,
    generate_pdv_book_csv,
    generate_pdv_book_xlsx,
)
from app.services.export.xlsx import generate_xlsx
from app.services.minimax.client import MiniMaxClient, MiniMaxError
from app.services.minimax.mapper import map_invoice_to_received, validate_invoice_for_minimax
from app.services.storage import get_presigned_url

logger = logging.getLogger(__name__)

router = APIRouter()

# Content types and file extensions per format
FORMAT_CONFIG = {
    "xlsx": {
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "extension": "xlsx",
    },
    "csv": {
        "content_type": "text/csv; charset=utf-8",
        "extension": "csv",
    },
    "json": {
        "content_type": "application/json; charset=utf-8",
        "extension": "json",
    },
    "minimax_xml": {
        "content_type": "application/xml; charset=utf-8",
        "extension": "xml",
    },
}


@router.post(
    "",
    responses={
        200: {"description": "Export file stream"},
        422: {"model": ExportBlockedResponse, "description": "Invoices blocked from export"},
    },
)
async def create_export(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("operator")),
) -> StreamingResponse:
    """Export invoices to the specified format.

    Streams the file directly as a response (XLSX, CSV, JSON, or MiniMax XML).
    Applies SRS 4.9.7 blocking rules before generating the export.
    Optionally applies a custom template for field selection and ordering.
    """
    # Load invoices scoped by organization
    try:
        invoices = await load_invoices_for_export(
            db, request.invoice_ids, current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Check export blocking rules (MiniMax XML has stricter verification rules).
    # When skip_validation=True, bypass Rules 1-3 (missing fields, low
    # confidence, unresolved warnings) but still enforce Rule 4 for MiniMax
    # XML which requires verified status.
    if not request.skip_validation:
        blocked = check_export_blocking(invoices, export_format=request.format)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "blocked_invoices": blocked,
                    "message": f"{len(blocked)} faktura blokirano za izvoz",
                },
            )
    elif request.format == "minimax_xml":
        # Even with skip_validation, MiniMax requires verified/exported status
        blocked = check_export_blocking(invoices, export_format="minimax_xml")
        minimax_blocked = [
            b for b in blocked if any("verifikovana" in r for r in b.get("reasons", []))
        ]
        if minimax_blocked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "blocked_invoices": minimax_blocked,
                    "message": "MiniMax XML zahteva verifikovane fakture",
                },
            )

    # Load template if specified
    template_fields = None
    opts = request.options
    if request.template_id and request.template_id != "default":
        template = await _load_template(db, request.template_id, current_user.organization_id)
        if template and template.fields:
            template_fields = template.fields
            # Apply template format overrides
            if template.date_format:
                opts.date_format = template.date_format
            if template.decimal_separator:
                opts.decimal_separator = template.decimal_separator

    # Generate export
    buffer = _generate_export(request.format, invoices, opts, template_fields)

    config = FORMAT_CONFIG[request.format]
    filename = _build_filename(invoices, config["extension"])

    logger.info(
        "Export generated: format=%s, invoices=%d, user=%s, template=%s",
        request.format,
        len(invoices),
        current_user.id,
        request.template_id,
    )

    return StreamingResponse(
        buffer,
        media_type=config["content_type"],
        headers={"Content-Disposition": _content_disposition(filename)},
    )


def _generate_export(
    fmt: str,
    invoices,
    opts,
    template_fields: list[dict] | None = None,
) -> BytesIO:
    """Dispatch to the appropriate format generator.

    Args:
        fmt: Export format string.
        invoices: List of Invoice instances.
        opts: ExportOptions instance.
        template_fields: Optional template field config for custom columns.

    Returns:
        BytesIO buffer with generated file content.
    """
    if fmt == "xlsx":
        return generate_xlsx(
            invoices,
            include_line_items=opts.include_line_items,
            date_format=opts.date_format,
            decimal_separator=opts.decimal_separator,
            template_fields=template_fields,
        )
    elif fmt == "csv":
        return generate_csv(
            invoices,
            date_format=opts.date_format,
            decimal_separator=opts.decimal_separator,
            delimiter=opts.delimiter,
            template_fields=template_fields,
        )
    elif fmt == "json":
        return generate_json(
            invoices,
            nested=opts.nested_json,
            date_format=opts.date_format,
            decimal_separator=opts.decimal_separator,
            template_fields=template_fields,
        )
    elif fmt == "minimax_xml":
        # MiniMax XML has a fixed schema — templates not applicable
        return generate_minimax_xml(invoices)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nepoznat format: {fmt}",
        )


async def _load_template(
    db: AsyncSession,
    template_id: str,
    organization_id: UUID,
) -> ExportTemplate | None:
    """Load a template by ID, enforcing org isolation.

    Args:
        db: Database session.
        template_id: Template UUID string.
        organization_id: Current user's organization.

    Returns:
        ExportTemplate instance or None if not found.
    """
    try:
        tid = UUID(template_id)
    except ValueError:
        return None

    result = await db.execute(
        select(ExportTemplate).where(
            ExportTemplate.id == tid,
            or_(
                ExportTemplate.organization_id.is_(None),
                ExportTemplate.organization_id == organization_id,
            ),
        )
    )
    return result.scalar_one_or_none()


def _content_disposition(filename: str) -> str:
    """Build Content-Disposition header value safe for non-ASCII filenames.

    Args:
        filename: The desired download filename (may contain Serbian chars).

    Returns:
        RFC 5987 encoded header value.
    """
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "export"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def _sanitize_filename(text: str) -> str:
    """Remove characters unsafe for filenames.

    Args:
        text: Raw text to sanitize.

    Returns:
        Filesystem-safe string with spaces replaced by underscores.
    """
    text = re.sub(r"[^\w\s\-.]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:50]


def _build_filename(invoices: list, extension: str) -> str:
    """Build a descriptive filename from invoice data.

    Single invoice: "{broj_fakture}_{prodavac}_{kupac}.{ext}"
    Multiple invoices: "fakture_{count}_{prodavac}.{ext}" (if same seller)
    or "fakture_{count}_izvoz.{ext}" (mixed sellers).

    Args:
        invoices: List of Invoice instances.
        extension: File extension (xlsx, csv, json, xml).

    Returns:
        Descriptive filename string.
    """
    if not invoices:
        return f"fakture_izvoz.{extension}"

    if len(invoices) == 1:
        inv = invoices[0]
        parts = []
        if inv.invoice_number:
            parts.append(_sanitize_filename(inv.invoice_number))
        seller = inv.seller if isinstance(inv.seller, dict) else {}
        buyer = inv.buyer if isinstance(inv.buyer, dict) else {}
        if seller.get("name"):
            parts.append(_sanitize_filename(seller["name"]))
        if buyer.get("name"):
            parts.append(_sanitize_filename(buyer["name"]))
        if parts:
            return f"{'_'.join(parts)}.{extension}"
        return f"faktura_izvoz.{extension}"

    # Multiple invoices
    sellers = set()
    for inv in invoices:
        seller = inv.seller if isinstance(inv.seller, dict) else {}
        if seller.get("name"):
            sellers.add(seller["name"])

    count = len(invoices)
    if len(sellers) == 1:
        seller_name = _sanitize_filename(next(iter(sellers)))
        return f"fakture_{count}_{seller_name}.{extension}"

    return f"fakture_{count}_izvoz.{extension}"


# ---------------------------------------------------------------------------
# Export Templates CRUD
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=list[ExportTemplateResponse])
async def list_export_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ExportTemplateResponse]:
    """List available export templates (system defaults + organization custom).

    Returns system-default templates (organization_id IS NULL) and any
    custom templates belonging to the current organization.
    """
    result = await db.execute(
        select(ExportTemplate)
        .where(
            or_(
                ExportTemplate.organization_id.is_(None),
                ExportTemplate.organization_id == current_user.organization_id,
            )
        )
        .order_by(ExportTemplate.is_default.desc(), ExportTemplate.name)
    )
    templates = result.scalars().all()
    return [ExportTemplateResponse.model_validate(t) for t in templates]


@router.post(
    "/templates",
    response_model=ExportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_export_template(
    data: ExportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("manager")),
) -> ExportTemplateResponse:
    """Create a custom export template for the organization.

    Validates that all field keys are recognized invoice field keys.
    """
    # Validate field keys
    invalid_keys = {f.key for f in data.fields} - VALID_FIELD_KEYS
    if invalid_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Nepoznati kljucevi polja: {', '.join(sorted(invalid_keys))}",
        )

    template = ExportTemplate(
        organization_id=current_user.organization_id,
        name=data.name,
        description=data.description,
        is_default=False,
        fields=[f.model_dump() for f in data.fields],
        date_format=data.date_format,
        decimal_separator=data.decimal_separator,
        supported_formats=data.supported_formats,
        created_by=current_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(
        "Export template created: id=%s, name=%s, org=%s",
        template.id,
        template.name,
        current_user.organization_id,
    )
    return ExportTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}", response_model=ExportTemplateResponse)
async def get_export_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ExportTemplateResponse:
    """Get a single export template by ID.

    Returns system defaults or templates owned by the current organization.
    """
    result = await db.execute(
        select(ExportTemplate).where(
            ExportTemplate.id == template_id,
            or_(
                ExportTemplate.organization_id.is_(None),
                ExportTemplate.organization_id == current_user.organization_id,
            ),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sablon nije pronadjen",
        )
    return ExportTemplateResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=ExportTemplateResponse)
async def update_export_template(
    template_id: UUID,
    data: ExportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("manager")),
) -> ExportTemplateResponse:
    """Update a custom export template.

    System default templates cannot be modified.
    """
    result = await db.execute(
        select(ExportTemplate).where(
            ExportTemplate.id == template_id,
            ExportTemplate.organization_id == current_user.organization_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sablon nije pronadjen",
        )
    if template.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sistemski sabloni ne mogu biti izmenjeni",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Validate field keys if fields are being updated
    if "fields" in update_data and update_data["fields"]:
        invalid_keys = {f["key"] for f in update_data["fields"]} - VALID_FIELD_KEYS
        if invalid_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Nepoznati kljucevi polja: {', '.join(sorted(invalid_keys))}",
            )
        # Convert TemplateField models to dicts
        update_data["fields"] = [
            f.model_dump() if hasattr(f, "model_dump") else f for f in update_data["fields"]
        ]

    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return ExportTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("manager")),
) -> None:
    """Delete a custom export template.

    System default templates cannot be deleted.
    """
    result = await db.execute(
        select(ExportTemplate).where(
            ExportTemplate.id == template_id,
            ExportTemplate.organization_id == current_user.organization_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sablon nije pronadjen",
        )
    if template.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sistemski sabloni ne mogu biti obrisani",
        )

    await db.delete(template)
    await db.commit()


# ---------------------------------------------------------------------------
# PDV Books (KPR / KIR)
# ---------------------------------------------------------------------------


@router.get(
    "/pdv-books/preview",
    response_model=PdvBookPreviewResponse,
    dependencies=[Depends(require_feature(Feature.PDV_BOOKS))],
)
async def preview_pdv_book(
    book_type: str,
    period: str,
    client_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("operator")),
) -> PdvBookPreviewResponse:
    """Preview entry count for a KPR/KIR book period.

    Args:
        book_type: KPR or KIR.
        period: Period in YYYY-MM format.
        client_id: Optional client filter for agency users.

    Returns:
        Entry count, period, and book type.
    """
    if book_type not in ("KPR", "KIR"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tip knjige mora biti KPR ili KIR",
        )

    entries = await fetch_pdv_book_entries(
        db, current_user.organization_id, period, book_type, client_id
    )
    return PdvBookPreviewResponse(
        entry_count=len(entries),
        period=period,
        book_type=book_type,
    )


@router.post(
    "/pdv-books",
    dependencies=[Depends(require_feature(Feature.PDV_BOOKS))],
)
async def generate_pdv_book(
    request: PdvBookRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("operator")),
) -> StreamingResponse:
    """Generate a KPR or KIR book for a given period.

    Streams the file as XLSX or CSV with proper Serbian headers and totals.

    Args:
        request: Book type, period, format, and optional client filter.

    Returns:
        StreamingResponse with the generated file.
    """
    entries = await fetch_pdv_book_entries(
        db,
        current_user.organization_id,
        request.period,
        request.book_type,
        request.client_id,
    )

    if request.format == "xlsx":
        buffer = generate_pdv_book_xlsx(entries, request.book_type, request.period)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        buffer = generate_pdv_book_csv(entries, request.book_type, request.period)
        content_type = "text/csv; charset=utf-8"
        ext = "csv"

    filename = f"{request.book_type}_{request.period}.{ext}"

    logger.info(
        "PDV book generated: type=%s, period=%s, entries=%d, format=%s, user=%s",
        request.book_type,
        request.period,
        len(entries),
        request.format,
        current_user.id,
    )

    return StreamingResponse(
        buffer,
        media_type=content_type,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


# ---------------------------------------------------------------------------
# Audit Export
# ---------------------------------------------------------------------------


@router.post(
    "/audit",
    response_model=AuditExportResponse,
    dependencies=[Depends(require_feature(Feature.AUDIT_EXPORT))],
)
async def create_audit_export(
    request: AuditExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
) -> AuditExportResponse:
    """Create audit export for tax inspection (admin only).

    Generates comprehensive export including:
    - Invoice register (CSV)
    - Original documents (PDF)
    - Audit trail (CSV)
    - VAT summary (XLSX)

    Uploads ZIP to S3 and returns presigned URL. Files are retained for 30 days;
    presigned URLs are regenerated on-demand via the history endpoint.
    Records the export in the scheduled_export_logs table for tracking.
    """

    try:
        date_from = date.fromisoformat(request.date_from)
        date_to = date.fromisoformat(request.date_to)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neispravan format datuma. Koristite YYYY-MM-DD.",
        )

    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datum od ne moze biti posle datuma do.",
        )

    # Create tracking record
    audit_export = ScheduledExportLog(
        organization_id=current_user.organization_id,
        export_type="manual",
        delivery_method="manual",
        delivered_to="",
        period=date_from.strftime("%Y-%m"),
        requested_by=current_user.id,
        date_from=date_from,
        date_to=date_to,
        reason=request.reason,
        status="processing",
        include_documents=request.include_documents,
        include_audit_trail=request.include_audit_trail,
        include_vat_summary=request.include_vat_summary,
    )
    db.add(audit_export)
    await db.commit()
    await db.refresh(audit_export)

    # Generate export
    result = await generate_audit_export(
        db=db,
        organization_id=current_user.organization_id,
        date_from=date_from,
        date_to=date_to,
        include_documents=request.include_documents,
        include_audit_trail=request.include_audit_trail,
        include_vat_summary=request.include_vat_summary,
    )

    # Update tracking record with results
    audit_export.status = "ready"
    audit_export.file_path = result["s3_key"]
    audit_export.file_size_bytes = result["file_size"]
    audit_export.invoice_count = result["invoice_count"]
    audit_export.download_url = result["download_url"]
    audit_export.expires_at = datetime.now(UTC) + timedelta(days=30)
    audit_export.delivered_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(audit_export)

    logger.info(
        "Audit export created: id=%s, org=%s, period=%s to %s",
        audit_export.id,
        current_user.organization_id,
        date_from,
        date_to,
    )

    return AuditExportResponse(
        id=audit_export.id,
        download_url=audit_export.download_url,
        file_size=audit_export.file_size_bytes,
        invoice_count=audit_export.invoice_count,
        period=result["period"],
        status=audit_export.status,
        reason=audit_export.reason,
        expires_at=audit_export.expires_at,
        created_at=audit_export.created_at,
    )


@router.get(
    "/audit/preview",
    dependencies=[Depends(require_feature(Feature.AUDIT_EXPORT))],
)
async def preview_audit_export(
    date_from: str,
    date_to: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
) -> dict:
    """Preview invoice count for a date range before generating audit export.

    Args:
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).

    Returns:
        Dict with invoice_count for the selected period.
    """
    try:
        d_from = date.fromisoformat(date_from)
        d_to = date.fromisoformat(date_to)
    except ValueError:
        return {"invoice_count": 0}

    effective_date = func.coalesce(Invoice.invoice_date, cast(Invoice.created_at, Date))
    result = await db.execute(
        select(func.count())
        .select_from(Invoice)
        .where(
            Invoice.organization_id == current_user.organization_id,
            effective_date >= d_from,
            effective_date <= d_to,
        )
    )
    count = result.scalar() or 0
    return {"invoice_count": count}


@router.get(
    "/audit/history",
    response_model=list[AuditExportResponse],
    dependencies=[Depends(require_feature(Feature.AUDIT_EXPORT))],
)
async def list_audit_exports(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
) -> list[AuditExportResponse]:
    """List past audit exports for the organization (admin only).

    Returns all audit export records ordered by creation date (newest first).
    """

    result = await db.execute(
        select(ScheduledExportLog)
        .where(
            ScheduledExportLog.organization_id == current_user.organization_id,
            ScheduledExportLog.export_type == "manual",
        )
        .order_by(ScheduledExportLog.delivered_at.desc())
    )
    exports = result.scalars().all()

    responses = []
    now = datetime.now(UTC)
    for e in exports:
        # Auto-expire if past expiration date
        export_status = e.status
        if export_status == "ready" and e.expires_at and e.expires_at < now:
            export_status = "expired"

        # Generate fresh presigned URL for ready exports with a stored S3 key
        download_url = None
        if export_status == "ready" and e.file_path:
            try:
                download_url = get_presigned_url(e.file_path, AUDIT_URL_EXPIRY)
            except Exception:
                logger.warning("Failed to generate presigned URL for export %s", e.id)
                download_url = None

        responses.append(
            AuditExportResponse(
                id=e.id,
                download_url=download_url,
                file_size=e.file_size_bytes,
                invoice_count=e.invoice_count,
                period={"from": e.date_from.isoformat(), "to": e.date_to.isoformat()},
                status=export_status,
                reason=e.reason,
                expires_at=e.expires_at,
                created_at=e.delivered_at,
            )
        )

    return responses


# ---------------------------------------------------------------------------
# MiniMax API integration
# ---------------------------------------------------------------------------


@router.post(
    "/minimax/push",
    response_model=MiniMaxPushResponse,
    dependencies=[Depends(require_feature(Feature.MINIMAX_DIRECT_PUSH))],
)
async def push_to_minimax(
    request: MiniMaxPushRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("operator")),
) -> MiniMaxPushResponse:
    """Push invoices to MiniMax accounting software via REST API.

    Requires MiniMax configuration to be set up for the organization.
    Creates customers in MiniMax if not found and create_customers is True.
    """
    # Load MiniMax config for this organization
    config = await _get_minimax_config(db, current_user.organization_id)

    # Load invoices
    try:
        invoices = await load_invoices_for_export(
            db, request.invoice_ids, current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Initialize client
    client = MiniMaxClient(
        client_id=config.client_id,
        client_secret=config.client_secret,
        username=config.username,
        password=config.password,
        org_id=config.minimax_org_id,
    )

    results: list[MiniMaxPushResult] = []

    for inv in invoices:
        try:
            # Validate invoice before sending
            validation = validate_invoice_for_minimax(inv)
            if validation["errors"]:
                results.append(
                    MiniMaxPushResult(
                        invoice_id=inv.id,
                        invoice_number=inv.invoice_number,
                        status="error",
                        error="; ".join(validation["errors"]),
                    )
                )
                continue

            # Find/create customer
            seller = inv.seller if isinstance(inv.seller, dict) else {}
            pib = seller.get("pib", "")

            if request.create_customers:
                customer = await client.find_or_create_customer(
                    pib=pib,
                    name=seller.get("name", "Nepoznat"),
                    address=seller.get("address", ""),
                    city=seller.get("city", ""),
                    postal_code=seller.get("postal_code", ""),
                )
            else:
                customer = await client.find_customer_by_pib(pib)
                if not customer:
                    results.append(
                        MiniMaxPushResult(
                            invoice_id=inv.id,
                            invoice_number=inv.invoice_number,
                            status="error",
                            error=f"Kupac sa PIB {pib} nije pronadjen u MiniMax-u",
                        )
                    )
                    continue

            # MiniMax may return a list or dict depending on the endpoint
            if isinstance(customer, list):
                customer = customer[0] if customer else {}
            customer_id = (
                customer.get("CustomerID") or customer.get("CustomerId") or customer.get("ID")
            )

            # Look up currency
            currency_id = None
            if inv.currency and inv.currency != "RSD":
                currency = await client.get_currency(inv.currency)
                if currency:
                    currency_id = currency.get("CurrencyID") or currency.get("ID")

            # Map and push invoice
            payload = map_invoice_to_received(inv, customer_id, currency_id)
            logger.info(
                "MiniMax payload for invoice %s: %s",
                inv.id,
                json.dumps(payload, default=str),
            )
            response = await client.push_received_invoice(payload)

            # MiniMax POST returns [] on success — look up the ID by DocumentReference
            minimax_id = None
            if isinstance(response, dict):
                minimax_id = response.get("ReceivedInvoiceId") or response.get("ID")
            elif isinstance(response, list) and not response:
                # Empty list = success, fetch the ID
                try:
                    all_invoices = await client._request("GET", "receivedinvoices")
                    rows = (
                        all_invoices.get("Rows", [])
                        if isinstance(all_invoices, dict)
                        else all_invoices
                    )
                    doc_ref = inv.invoice_number or ""
                    for row in rows:
                        if row.get("DocumentReference") == doc_ref:
                            minimax_id = row.get("ReceivedInvoiceId")
                            break
                except Exception:
                    logger.warning("Could not fetch MiniMax ID for %s", inv.id)
            results.append(
                MiniMaxPushResult(
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    minimax_id=minimax_id,
                    status="success",
                )
            )

            logger.info(
                "MiniMax push success: invoice=%s → minimax_id=%s",
                inv.id,
                minimax_id,
            )

        except MiniMaxError as e:
            # Provide user-friendly error for duplicates
            if e.status_code == 409 and "originalni broj" in (e.response_body or "").lower():
                msg = f"Faktura '{inv.invoice_number}' već postoji u MiniMax-u"
            else:
                msg = str(e)
            logger.error(
                "MiniMax push failed for invoice %s: %s (body: %s)",
                inv.id,
                e,
                getattr(e, "response_body", None),
            )
            results.append(
                MiniMaxPushResult(
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    status="error",
                    error=msg,
                )
            )

    # Mark successfully pushed invoices as "exported"
    success_ids = {r.invoice_id for r in results if r.status == "success"}
    if success_ids:
        for inv in invoices:
            if inv.id in success_ids:
                inv.status = "exported"
        await db.commit()

    success_count = sum(1 for r in results if r.status == "success")
    return MiniMaxPushResponse(
        results=results,
        total=len(results),
        success_count=success_count,
        error_count=len(results) - success_count,
    )


@router.get("/minimax/config", response_model=MiniMaxConfigResponse)
async def get_minimax_config_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MiniMaxConfigResponse:
    """Get MiniMax configuration for the current organization."""
    config = await _get_minimax_config(db, current_user.organization_id)
    return MiniMaxConfigResponse.model_validate(config)


@router.put("/minimax/config", response_model=MiniMaxConfigResponse)
async def upsert_minimax_config(
    data: MiniMaxConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
) -> MiniMaxConfigResponse:
    """Create or update MiniMax configuration for the organization."""
    result = await db.execute(
        select(MiniMaxConfig).where(MiniMaxConfig.organization_id == current_user.organization_id)
    )
    config = result.scalar_one_or_none()

    if config:
        config.client_id = data.client_id
        # Only update secrets if non-empty (frontend sends empty when unchanged)
        if data.client_secret:
            config.client_secret = data.client_secret
        config.username = data.username
        if data.password:
            config.password = data.password
        config.minimax_org_id = data.minimax_org_id
    else:
        config = MiniMaxConfig(
            organization_id=current_user.organization_id,
            client_id=data.client_id,
            client_secret=data.client_secret,
            username=data.username,
            password=data.password,
            minimax_org_id=data.minimax_org_id,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    logger.info("MiniMax config saved for org %s", current_user.organization_id)
    return MiniMaxConfigResponse.model_validate(config)


@router.patch("/minimax/config", response_model=MiniMaxConfigResponse)
async def update_minimax_config(
    data: MiniMaxConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
) -> MiniMaxConfigResponse:
    """Partially update MiniMax configuration."""
    config = await _get_minimax_config(db, current_user.organization_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return MiniMaxConfigResponse.model_validate(config)


@router.post("/minimax/test-connection")
async def test_minimax_connection(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
) -> dict:
    """Test MiniMax connection using saved credentials.

    Args:
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Connection status with message.
    """
    result = await db.execute(
        select(MiniMaxConfig).where(MiniMaxConfig.organization_id == current_user.organization_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MiniMax konfiguracija nije postavljena.",
        )

    try:
        from app.services.minimax.client import MiniMaxClient

        client = MiniMaxClient(
            client_id=config.client_id,
            client_secret=config.client_secret,
            username=config.username,
            password=config.password,
            org_id=config.minimax_org_id,
        )
        await client.authenticate()
        return {"status": "connected", "message": "Uspešno povezano sa MiniMax"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Neuspešna veza: {exc}",
        )


async def _get_minimax_config(db: AsyncSession, organization_id) -> MiniMaxConfig:
    """Load MiniMax config or raise 404.

    Args:
        db: Database session.
        organization_id: Organization UUID.

    Returns:
        MiniMaxConfig instance.

    Raises:
        HTTPException: If config not found.
    """
    result = await db.execute(
        select(MiniMaxConfig).where(MiniMaxConfig.organization_id == organization_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MiniMax konfiguracija nije postavljena. Koristite PUT /export/minimax/config.",
        )
    if not config.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="MiniMax integracija je deaktivirana.",
        )
    return config
