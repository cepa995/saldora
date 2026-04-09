"""Scheduled archive export service.

Generates monthly archive ZIPs and delivers them to organizations
via email. Reuses the audit export service for ZIP generation.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
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

    try:
        from app.services.email import send_archive_email

        await send_archive_email(
            to_email=email_to,
            org_name=organization.name or "",
            period=period,
            invoice_count=archive_result.get("invoice_count", 0),
            download_url=archive_result.get("download_url", ""),
        )
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
    file_path: str | None = None,
    download_url: str | None = None,
    expires_at: datetime | None = None,
    export_type: str = "scheduled",
    requested_by: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reason: str | None = None,
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
        file_path: S3 key to the generated archive ZIP.
        download_url: Presigned download URL.
        expires_at: When the download link expires.
        export_type: 'scheduled' or 'manual'.
        requested_by: User UUID who requested a manual export.
        date_from: Start date for manual exports.
        date_to: End date for manual exports.
        reason: Reason for manual export.
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
        export_type=export_type,
        file_path=file_path,
        download_url=download_url,
        expires_at=expires_at,
        requested_by=requested_by,
        date_from=date_from,
        date_to=date_to,
        reason=reason,
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
            "download_url": log.download_url,
            "file_path": log.file_path,
            "export_type": log.export_type,
            "date_from": log.date_from.isoformat() if log.date_from else None,
            "date_to": log.date_to.isoformat() if log.date_to else None,
            "reason": log.reason,
            "expires_at": log.expires_at.isoformat() if log.expires_at else None,
        }
        for log in logs
    ]
