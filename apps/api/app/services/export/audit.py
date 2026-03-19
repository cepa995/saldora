"""Audit export service — generates comprehensive ZIP for tax inspections.

Creates a ZIP archive containing:
- registar_faktura.csv — invoice register
- pdv_pregled.xlsx — VAT summary by rate and period
- revizijski_trag.csv — audit trail from audit_logs
- dokumenti/ — original PDF documents from S3

Uploads the ZIP to S3 and returns a presigned URL.
"""

import asyncio
import csv
import logging
import zipfile
from datetime import date, datetime
from io import BytesIO, StringIO
from uuid import UUID

from openpyxl import Workbook
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.invoice import Invoice
from app.services.export.core import (
    format_serbian_date,
    format_serbian_number,
)
from app.services.storage import get_presigned_url, get_s3_client

logger = logging.getLogger(__name__)

# UTF-8 BOM for CSV Excel compatibility
UTF8_BOM = b"\xef\xbb\xbf"

# Presigned URL expiry — S3 max is 7 days (604800s).
# We use 1 hour here since URLs are regenerated on-demand in the history endpoint.
AUDIT_URL_EXPIRY = 3600


async def generate_audit_export(
    db: AsyncSession,
    organization_id: UUID,
    date_from: date,
    date_to: date,
    include_documents: bool = True,
    include_audit_trail: bool = True,
    include_vat_summary: bool = True,
) -> dict:
    """Generate audit export ZIP and upload to S3.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        date_from: Start date for the export period.
        date_to: End date for the export period.
        include_documents: Whether to include original PDFs.
        include_audit_trail: Whether to include audit trail CSV.
        include_vat_summary: Whether to include VAT summary XLSX.

    Returns:
        Dict with download_url, file_size, and metadata.
    """
    # Load invoices in date range.
    # Use COALESCE so invoices without an extracted date fall back to created_at.
    effective_date = func.coalesce(Invoice.invoice_date, cast(Invoice.created_at, Date))
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.organization_id == organization_id,
            effective_date >= date_from,
            effective_date <= date_to,
        )
        .order_by(effective_date)
    )
    invoices = list(result.scalars().all())

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Invoice register CSV
        register_csv = _build_invoice_register(invoices)
        zf.writestr("registar_faktura.csv", register_csv)

        # 2. VAT summary XLSX
        if include_vat_summary:
            vat_xlsx = _build_vat_summary(invoices)
            zf.writestr("pdv_pregled.xlsx", vat_xlsx)

        # 3. Audit trail CSV
        if include_audit_trail:
            audit_csv = await _build_audit_trail(db, organization_id, date_from, date_to)
            zf.writestr("revizijski_trag.csv", audit_csv)

        # 4. Original documents from S3
        if include_documents:
            await _add_documents(zf, invoices)

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.getvalue()

    # Upload to S3
    key = f"organizations/{organization_id}/exports/audit_{date_from}_{date_to}.zip"
    client = get_s3_client()
    await asyncio.to_thread(
        client.put_object,
        Bucket="saldora-documents",
        Key=key,
        Body=zip_bytes,
        ContentType="application/zip",
    )

    download_url = await asyncio.to_thread(
        get_presigned_url,
        key,
        AUDIT_URL_EXPIRY,
    )

    logger.info(
        "Audit export generated: org=%s, period=%s to %s, invoices=%d, size=%d bytes",
        organization_id,
        date_from,
        date_to,
        len(invoices),
        len(zip_bytes),
    )

    return {
        "download_url": download_url,
        "file_size": len(zip_bytes),
        "invoice_count": len(invoices),
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "s3_key": key,
    }


def _build_invoice_register(invoices: list[Invoice]) -> bytes:
    """Build invoice register CSV.

    Args:
        invoices: List of Invoice instances.

    Returns:
        UTF-8 encoded CSV bytes with BOM.
    """
    buf = StringIO()
    writer = csv.writer(buf, delimiter=";")

    # Header
    writer.writerow(
        [
            "Broj fakture",
            "Datum fakture",
            "Datum valute",
            "Prodavac",
            "PIB prodavca",
            "Kupac",
            "PIB kupca",
            "Osnovica",
            "Stopa PDV",
            "Iznos PDV",
            "Ukupan iznos",
            "Valuta",
            "Status",
        ]
    )

    for inv in invoices:
        seller = inv.seller if isinstance(inv.seller, dict) else {}
        buyer = inv.buyer if isinstance(inv.buyer, dict) else {}
        writer.writerow(
            [
                inv.invoice_number or "",
                format_serbian_date(inv.invoice_date),
                format_serbian_date(inv.due_date),
                seller.get("name", ""),
                seller.get("pib", ""),
                buyer.get("name", ""),
                buyer.get("pib", ""),
                format_serbian_number(inv.subtotal),
                format_serbian_number(inv.tax_rate),
                format_serbian_number(inv.tax_amount),
                format_serbian_number(inv.total_amount),
                inv.currency or "RSD",
                inv.status or "",
            ]
        )

    return UTF8_BOM + buf.getvalue().encode("utf-8")


def _build_vat_summary(invoices: list[Invoice]) -> bytes:
    """Build VAT summary XLSX grouped by rate.

    Args:
        invoices: List of Invoice instances.

    Returns:
        XLSX file bytes.
    """
    # Group by tax rate
    by_rate: dict[str, dict] = {}
    for inv in invoices:
        rate_key = str(inv.tax_rate or "0")
        if rate_key not in by_rate:
            by_rate[rate_key] = {"base": 0.0, "tax": 0.0, "total": 0.0, "count": 0}
        entry = by_rate[rate_key]
        entry["base"] += float(inv.subtotal or 0)
        entry["tax"] += float(inv.tax_amount or 0)
        entry["total"] += float(inv.total_amount or 0)
        entry["count"] += 1

    wb = Workbook()
    ws = wb.active
    ws.title = "PDV pregled"

    ws.append(["Stopa PDV (%)", "Broj faktura", "Osnovica", "Iznos PDV", "Ukupno"])

    for rate, data in sorted(by_rate.items()):
        ws.append(
            [
                rate,
                data["count"],
                format_serbian_number(data["base"]),
                format_serbian_number(data["tax"]),
                format_serbian_number(data["total"]),
            ]
        )

    # Totals row
    ws.append(
        [
            "UKUPNO",
            sum(d["count"] for d in by_rate.values()),
            format_serbian_number(sum(d["base"] for d in by_rate.values())),
            format_serbian_number(sum(d["tax"] for d in by_rate.values())),
            format_serbian_number(sum(d["total"] for d in by_rate.values())),
        ]
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _build_audit_trail(
    db: AsyncSession,
    organization_id: UUID,
    date_from: date,
    date_to: date,
) -> bytes:
    """Build audit trail CSV from audit_logs table.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        date_from: Start date.
        date_to: End date.

    Returns:
        UTF-8 encoded CSV bytes with BOM.
    """
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.organization_id == organization_id,
            AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()),
            AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()),
        )
        .order_by(AuditLog.created_at)
    )
    logs = result.scalars().all()

    buf = StringIO()
    writer = csv.writer(buf, delimiter=";")

    writer.writerow(
        [
            "Datum i vreme",
            "Akcija",
            "Korisnik ID",
            "Tip entiteta",
            "Entitet ID",
            "IP adresa",
        ]
    )

    for log in logs:
        writer.writerow(
            [
                log.created_at.isoformat() if log.created_at else "",
                log.action or "",
                str(log.user_id) if log.user_id else "",
                log.entity_type or "",
                str(log.entity_id) if log.entity_id else "",
                log.ip_address or "",
            ]
        )

    return UTF8_BOM + buf.getvalue().encode("utf-8")


async def _add_documents(zf: zipfile.ZipFile, invoices: list[Invoice]) -> None:
    """Download and add original documents from S3 to the ZIP.

    Args:
        zf: Open ZipFile to write to.
        invoices: Invoices with document_path set.
    """
    client = get_s3_client()

    for inv in invoices:
        if not inv.document_path:
            continue
        try:
            response = await asyncio.to_thread(
                client.get_object,
                Bucket="saldora-documents",
                Key=inv.document_path,
            )
            body = await asyncio.to_thread(response["Body"].read)

            # Use invoice number or ID for the filename
            ext = inv.document_content_type.split("/")[-1] if inv.document_content_type else "pdf"
            name = inv.invoice_number or str(inv.id)
            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
            zf.writestr(f"dokumenti/{safe_name}.{ext}", body)
        except Exception:
            logger.warning("Failed to fetch document for invoice %s", inv.id, exc_info=True)
