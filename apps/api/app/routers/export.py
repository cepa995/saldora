"""Export router - generate exports in various formats."""

import logging
import re
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.minimax_config import MiniMaxConfig
from app.schemas.export import AuditExportRequest, ExportBlockedResponse, ExportRequest
from app.schemas.minimax import (
    MiniMaxConfigCreate,
    MiniMaxConfigResponse,
    MiniMaxConfigUpdate,
    MiniMaxPushRequest,
    MiniMaxPushResponse,
    MiniMaxPushResult,
)
from app.services.export.audit import generate_audit_export
from app.services.export.core import (
    check_export_blocking,
    load_invoices_for_export,
)
from app.services.export.csv_gen import generate_csv
from app.services.export.json_gen import generate_json
from app.services.export.minimax_xml import generate_minimax_xml
from app.services.export.xlsx import generate_xlsx
from app.services.minimax.client import MiniMaxClient, MiniMaxError
from app.services.minimax.mapper import map_invoice_to_received

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
    current_user=Depends(get_current_user),
) -> StreamingResponse:
    """Export invoices to the specified format.

    Streams the file directly as a response (XLSX, CSV, JSON, or MiniMax XML).
    Applies SRS 4.9.7 blocking rules before generating the export.
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

    # Check export blocking rules (MiniMax XML has stricter verification rules)
    blocked = check_export_blocking(invoices, export_format=request.format)
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "blocked_invoices": blocked,
                "message": f"{len(blocked)} faktura blokirano za izvoz",
            },
        )

    # Generate export
    opts = request.options
    buffer = _generate_export(request.format, invoices, opts)

    config = FORMAT_CONFIG[request.format]
    filename = _build_filename(invoices, config["extension"])

    logger.info(
        "Export generated: format=%s, invoices=%d, user=%s",
        request.format,
        len(invoices),
        current_user.id,
    )

    return StreamingResponse(
        buffer,
        media_type=config["content_type"],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _generate_export(fmt: str, invoices, opts) -> BytesIO:
    """Dispatch to the appropriate format generator.

    Args:
        fmt: Export format string.
        invoices: List of Invoice instances.
        opts: ExportOptions instance.

    Returns:
        BytesIO buffer with generated file content.
    """
    if fmt == "xlsx":
        return generate_xlsx(
            invoices,
            include_line_items=opts.include_line_items,
            date_format=opts.date_format,
            decimal_separator=opts.decimal_separator,
        )
    elif fmt == "csv":
        return generate_csv(
            invoices,
            date_format=opts.date_format,
            decimal_separator=opts.decimal_separator,
            delimiter=opts.delimiter,
        )
    elif fmt == "json":
        return generate_json(
            invoices,
            nested=opts.nested_json,
            date_format=opts.date_format,
            decimal_separator=opts.decimal_separator,
        )
    elif fmt == "minimax_xml":
        return generate_minimax_xml(invoices)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nepoznat format: {fmt}",
        )


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


@router.get("/templates")
async def list_export_templates(
    current_user=Depends(get_current_user),
) -> list[dict]:
    """List available export templates."""
    return [
        {
            "id": "default",
            "name": "Standardni izvoz",
            "description": "Sva polja u standardnom redosledu",
            "formats": ["xlsx", "csv", "json"],
        },
        {
            "id": "accounting",
            "name": "Računovodstveni izvoz",
            "description": "Polja za knjiženje u računovodstveni softver",
            "formats": ["xlsx", "csv", "json"],
        },
        {
            "id": "minimax",
            "name": "MiniMax izvoz",
            "description": "Format za uvoz u MiniMax računovodstveni softver",
            "formats": ["minimax_xml"],
        },
        {
            "id": "tax",
            "name": "PDV evidencija",
            "description": "Format za PDV prijavu",
            "formats": ["xlsx", "csv"],
        },
    ]


@router.post("/audit")
async def create_audit_export(
    request: AuditExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Create audit export for tax inspection.

    Generates comprehensive export including:
    - Invoice register (CSV)
    - Original documents (PDF)
    - Audit trail (CSV)
    - VAT summary (XLSX)

    Uploads ZIP to S3 and returns presigned URL (30-day expiry).
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
            detail="Datum od ne može biti posle datuma do.",
        )

    result = await generate_audit_export(
        db=db,
        organization_id=current_user.organization_id,
        date_from=date_from,
        date_to=date_to,
        include_documents=request.include_documents,
        include_audit_trail=request.include_audit_trail,
        include_vat_summary=request.include_vat_summary,
    )
    return result


# ---------------------------------------------------------------------------
# MiniMax API integration
# ---------------------------------------------------------------------------


@router.post("/minimax/push", response_model=MiniMaxPushResponse)
async def push_to_minimax(
    request: MiniMaxPushRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
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
            # Find/create customer
            seller = inv.seller if isinstance(inv.seller, dict) else {}
            pib = seller.get("pib", "")
            if not pib:
                results.append(
                    MiniMaxPushResult(
                        invoice_id=inv.id,
                        invoice_number=inv.invoice_number,
                        status="error",
                        error="Nedostaje PIB prodavca",
                    )
                )
                continue

            if request.create_customers:
                customer = await client.find_or_create_customer(
                    pib=pib,
                    name=seller.get("name", "Nepoznat"),
                    address=seller.get("address", ""),
                    city=seller.get("city", ""),
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

            customer_id = customer.get("CustomerID") or customer.get("ID")

            # Look up currency
            currency_id = None
            if inv.currency and inv.currency != "RSD":
                currency = await client.get_currency(inv.currency)
                if currency:
                    currency_id = currency.get("CurrencyID") or currency.get("ID")

            # Map and push invoice
            payload = map_invoice_to_received(inv, customer_id, currency_id)
            response = await client.push_received_invoice(payload)

            minimax_id = response.get("ReceivedInvoiceID") or response.get("ID")
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
            logger.error("MiniMax push failed for invoice %s: %s", inv.id, e)
            results.append(
                MiniMaxPushResult(
                    invoice_id=inv.id,
                    invoice_number=inv.invoice_number,
                    status="error",
                    error=str(e),
                )
            )

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
    current_user=Depends(get_current_user),
) -> MiniMaxConfigResponse:
    """Create or update MiniMax configuration for the organization."""
    result = await db.execute(
        select(MiniMaxConfig).where(MiniMaxConfig.organization_id == current_user.organization_id)
    )
    config = result.scalar_one_or_none()

    if config:
        config.client_id = data.client_id
        config.client_secret = data.client_secret
        config.username = data.username
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
    current_user=Depends(get_current_user),
) -> MiniMaxConfigResponse:
    """Partially update MiniMax configuration."""
    config = await _get_minimax_config(db, current_user.organization_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return MiniMaxConfigResponse.model_validate(config)


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
