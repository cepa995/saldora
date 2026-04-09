"""Scheduled archive export service.

Generates monthly archive ZIPs and delivers them to organizations
via email. Reuses the audit export service for ZIP generation.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.scheduled_export_log import ScheduledExportLog
from app.services.export.audit import generate_audit_export

logger = logging.getLogger(__name__)


async def generate_monthly_archive(
    db: AsyncSession,
    organization_id: UUID,
    period: str,
    include_pdfs: bool = True,
) -> dict:
    """Generate a monthly archive export for one organization.

    Reuses the audit export service to create a ZIP with invoices,
    PDFs, audit trail, and VAT summary for the given period.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        period: Period string like "2026-03".
        include_pdfs: Whether to include original PDF documents.

    Returns:
        Dict with download_url, file_size, invoice_count, s3_key.
    """
    year, month = period.split("-")
    date_from = date(int(year), int(month), 1)

    # Calculate last day of month
    if int(month) == 12:
        date_to = date(int(year) + 1, 1, 1)
    else:
        date_to = date(int(year), int(month) + 1, 1)
    from datetime import timedelta

    date_to = date_to - timedelta(days=1)

    result = await generate_audit_export(
        db=db,
        organization_id=organization_id,
        date_from=date_from,
        date_to=date_to,
        include_documents=include_pdfs,
        include_audit_trail=True,
        include_vat_summary=True,
    )

    return result


async def deliver_archive_via_email(
    organization: Organization,
    archive_result: dict,
    period: str,
) -> None:
    """Send the archive ZIP to the organization's billing email.

    Args:
        organization: Organization with billing_email.
        archive_result: Result from generate_monthly_archive.
        period: Period string like "2026-03".
    """
    email_to = organization.billing_email or ""
    if not email_to:
        logger.warning(
            "No billing email for org %s, skipping archive delivery",
            organization.id,
        )
        return

    subject = f"Saldora — Mesečni arhivski izvoz {period} — {organization.name}"
    body = f"""Poštovani,

U prilogu se nalazi automatski generisan arhivski izvoz vaših
faktura za period {period}.

Sadržaj arhive:
• Registar faktura (CSV)
• PDV pregled (Excel)
• Revizorski trag (CSV)
• Originalna PDF dokumenta

Broj faktura u periodu: {archive_result.get("invoice_count", 0)}

Preporučujemo da ovaj fajl sačuvate na sigurnom mestu kao deo
vaše računovodstvene arhive u skladu sa Zakonom o računovodstvu.

Link za preuzimanje (važi 24 sata):
{archive_result.get("download_url", "")}

Pozdrav,
Saldora tim

---
Ovo je automatska poruka. Podešavanja automatskog izvoza možete
promeniti na stranici Arhiviranje u aplikaciji.
"""

    try:
        from app.services.email import _send_email

        await _send_email(to_email=email_to, subject=subject, html=body)
        logger.info(
            "Archive for %s delivered to %s (%d invoices)",
            period,
            email_to,
            archive_result.get("invoice_count", 0),
        )
    except Exception:
        logger.exception(
            "Failed to deliver archive for org %s period %s",
            organization.id,
            period,
        )
        raise


async def log_export_delivery(
    db: AsyncSession,
    organization_id: UUID,
    period: str,
    delivered_to: str,
    file_size: int | None,
    invoice_count: int | None,
    status: str,
    error_message: str | None = None,
) -> None:
    """Log an archive export delivery attempt.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        period: Period string.
        delivered_to: Email address or path.
        file_size: ZIP file size in bytes.
        invoice_count: Number of invoices in the archive.
        status: 'delivered', 'failed', or 'skipped'.
        error_message: Error details if failed.
    """
    log = ScheduledExportLog(
        organization_id=organization_id,
        period=period,
        delivery_method="email",
        delivered_to=delivered_to,
        file_size_bytes=file_size,
        invoice_count=invoice_count,
        status=status,
        error_message=error_message,
    )
    db.add(log)
    await db.commit()


async def get_export_history(
    db: AsyncSession,
    organization_id: UUID,
    limit: int = 12,
) -> list[dict]:
    """Get recent export delivery history for an organization.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        limit: Max records to return.

    Returns:
        List of export log dicts.
    """
    result = await db.execute(
        select(ScheduledExportLog)
        .where(ScheduledExportLog.organization_id == organization_id)
        .order_by(ScheduledExportLog.delivered_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "period": log.period,
            "delivery_method": log.delivery_method,
            "delivered_to": log.delivered_to,
            "file_size_bytes": log.file_size_bytes,
            "invoice_count": log.invoice_count,
            "status": log.status,
            "error_message": log.error_message,
            "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
        }
        for log in logs
    ]
