"""Archive export router — automated monthly exports and on-demand archives.

Provides endpoints for:
- Viewing export delivery history
- Triggering on-demand archive generation
- Configuring automated monthly exports
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.organization import Organization
from app.models.user import User
from app.services.export.scheduled import get_export_history

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/history")
async def list_export_history(
    limit: int = Query(default=12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> list[dict]:
    """Get recent archive export delivery history.

    Args:
        limit: Max records to return.
        db: Database session.
        user: Authenticated user.

    Returns:
        List of export delivery log entries.
    """
    return await get_export_history(db, user.organization_id, limit)


@router.post("/generate")
async def trigger_archive_export(
    period: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Period YYYY-MM"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Generate and deliver an archive export.

    Runs the full archive pipeline in a background task: generates
    a ZIP (invoice CSV, VAT XLSX, audit CSV, PDFs), uploads to S3,
    and emails the download link. This is the same logic that runs
    automatically on the 1st of each month.

    Args:
        period: Period string like "2026-03".
        background_tasks: FastAPI background tasks.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Queued status with delivery email.
    """
    from sqlalchemy import select

    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organizacija nije pronađena")

    email_to = org.billing_email
    if not email_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organizacija nema podešen email za naplatu. "
            "Podesite billing email u Podešavanja → Organizacija.",
        )

    background_tasks.add_task(
        _run_archive_export,
        organization_id=user.organization_id,
        org_name=org.name or "",
        billing_email=email_to,
        period=period,
    )

    return {
        "status": "queued",
        "period": period,
        "delivered_to": email_to,
    }


async def _run_archive_export(
    organization_id,
    org_name: str,
    billing_email: str,
    period: str,
) -> None:
    """Background task: generate archive ZIP and email it.

    Creates its own DB session since the request session is closed
    by the time this runs.

    Args:
        organization_id: Org UUID.
        org_name: Organization name for email subject.
        billing_email: Delivery email.
        period: Period string like "2026-03".
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.services.export.scheduled import (
        deliver_archive_via_email,
        generate_monthly_archive,
        log_export_delivery,
    )

    s = get_settings()
    engine = create_async_engine(s.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with factory() as db:
            archive_result = await generate_monthly_archive(
                db, organization_id, period, include_pdfs=True
            )

            # Get org for email delivery
            result = await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org = result.scalar_one_or_none()

            if org:
                await deliver_archive_via_email(org, archive_result, period)

            await log_export_delivery(
                db=db,
                organization_id=organization_id,
                period=period,
                delivered_to=billing_email,
                file_size=archive_result.get("file_size"),
                invoice_count=archive_result.get("invoice_count"),
                status="delivered",
            )

            # Also create audit_export record for download history
            from datetime import date as date_type
            from datetime import timedelta

            from app.models.audit_export import AuditExport

            year, month = period.split("-")
            date_from_parsed = date_type(int(year), int(month), 1)
            if int(month) == 12:
                date_to_parsed = date_type(int(year) + 1, 1, 1) - timedelta(days=1)
            else:
                date_to_parsed = date_type(int(year), int(month) + 1, 1) - timedelta(days=1)

            audit_record = AuditExport(
                organization_id=organization_id,
                date_from=date_from_parsed,
                date_to=date_to_parsed,
                status="ready",
                file_path=archive_result.get("s3_key"),
                file_size_bytes=archive_result.get("file_size"),
                invoice_count=archive_result.get("invoice_count"),
                download_url=archive_result.get("download_url"),
                expires_at=datetime.now(UTC) + timedelta(days=30),
                include_documents=True,
                include_audit_trail=True,
                include_vat_summary=True,
            )
            db.add(audit_record)
            await db.commit()

        logger.info(
            "Archive delivered for %s period %s (%d invoices) to %s",
            org_name,
            period,
            archive_result.get("invoice_count", 0),
            billing_email,
        )
    except Exception as exc:
        logger.exception("Archive export failed for %s period %s", org_name, period)
        try:
            async with factory() as db:
                await log_export_delivery(
                    db=db,
                    organization_id=organization_id,
                    period=period,
                    delivered_to=billing_email,
                    file_size=None,
                    invoice_count=None,
                    status="failed",
                    error_message=str(exc)[:500],
                )
        except Exception:
            logger.exception("Failed to log archive failure")
    finally:
        await engine.dispose()


@router.post("/internal-generate")
async def internal_generate_archive(
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Internal endpoint called by Celery worker for automated monthly archives.

    No auth required — only accessible from internal network (worker → API).

    Args:
        body: Dict with org_id, period, billing_email, org_name.
        db: Database session.

    Returns:
        Result with status.
    """
    from uuid import UUID

    from app.services.export.scheduled import (
        deliver_archive_via_email,
        generate_monthly_archive,
        log_export_delivery,
    )

    org_id = UUID(body["org_id"])
    period = body["period"]
    billing_email = body["billing_email"]
    org_name = body.get("org_name", "")

    from sqlalchemy import select

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        return {"status": "failed", "error": "Organization not found"}

    try:
        archive_result = await generate_monthly_archive(db, org_id, period, include_pdfs=True)

        await deliver_archive_via_email(org, archive_result, period)

        await log_export_delivery(
            db=db,
            organization_id=org_id,
            period=period,
            delivered_to=billing_email,
            file_size=archive_result.get("file_size"),
            invoice_count=archive_result.get("invoice_count"),
            status="delivered",
        )

        return {
            "status": "delivered",
            "invoice_count": archive_result.get("invoice_count", 0),
        }

    except Exception as exc:
        await log_export_delivery(
            db=db,
            organization_id=org_id,
            period=period,
            delivered_to=billing_email,
            file_size=None,
            invoice_count=None,
            status="failed",
            error_message=str(exc)[:500],
        )
        logger.exception("Internal archive failed for %s period %s", org_name, period)
        return {"status": "failed", "error": str(exc)[:200]}


@router.get("/settings")
async def get_archive_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> dict:
    """Get archive export settings for the current organization.

    Returns:
        Archive settings including enabled status and email.
    """
    from sqlalchemy import select

    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    settings = org.settings if isinstance(org.settings, dict) else {}
    archive_settings = settings.get("archive_export", {})

    return {
        "enabled": archive_settings.get("enabled", True),
        "email": org.billing_email or "",
        "formats": archive_settings.get("formats", ["xlsx", "csv", "pdf"]),
        "include_pdfs": archive_settings.get("include_pdfs", True),
    }


@router.put("/settings")
async def update_archive_settings(
    enabled: bool = Query(default=True),
    include_pdfs: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Update archive export settings.

    Args:
        enabled: Whether automated monthly exports are enabled.
        include_pdfs: Whether to include original PDF documents.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Updated settings.
    """
    from sqlalchemy import select

    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()

    settings = org.settings if isinstance(org.settings, dict) else {}
    settings["archive_export"] = {
        "enabled": enabled,
        "include_pdfs": include_pdfs,
        "formats": ["xlsx", "csv", "pdf"],
    }
    org.settings = settings
    await db.commit()

    return {
        "enabled": enabled,
        "include_pdfs": include_pdfs,
        "email": org.billing_email or "",
        "formats": ["xlsx", "csv", "pdf"],
    }
