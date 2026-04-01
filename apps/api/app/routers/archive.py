"""Archive export router — automated monthly exports and on-demand archives.

Provides endpoints for:
- Viewing export delivery history
- Triggering on-demand archive generation
- Configuring automated monthly exports
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.organization import Organization
from app.models.user import User
from app.services.export.scheduled import (
    deliver_archive_via_email,
    generate_monthly_archive,
    get_export_history,
    log_export_delivery,
)

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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict:
    """Generate and deliver an archive export on demand.

    Creates a ZIP with all invoices, PDFs, audit trail, and VAT
    summary for the specified period. Delivers via email to the
    organization's billing email.

    Args:
        period: Period string like "2026-03".
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Export result with download URL and delivery status.
    """
    from sqlalchemy import select

    # Get organization
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

    try:
        # Generate archive
        archive_result = await generate_monthly_archive(db, user.organization_id, period)

        # Deliver via email
        await deliver_archive_via_email(org, archive_result, period)

        # Log success
        await log_export_delivery(
            db=db,
            organization_id=user.organization_id,
            period=period,
            delivered_to=email_to,
            file_size=archive_result.get("file_size"),
            invoice_count=archive_result.get("invoice_count"),
            status="delivered",
        )

        return {
            "status": "delivered",
            "period": period,
            "delivered_to": email_to,
            "invoice_count": archive_result.get("invoice_count", 0),
            "file_size": archive_result.get("file_size", 0),
            "download_url": archive_result.get("download_url"),
        }

    except Exception as exc:
        # Log failure
        await log_export_delivery(
            db=db,
            organization_id=user.organization_id,
            period=period,
            delivered_to=email_to or "unknown",
            file_size=None,
            invoice_count=None,
            status="failed",
            error_message=str(exc),
        )
        logger.exception("Archive export failed for org %s period %s", user.organization_id, period)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Greška pri generisanju arhive: {exc}",
        )


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
