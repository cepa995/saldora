"""Billing router — subscription info and usage stats."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.organization import Organization
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.plans import get_plan
from app.schemas.billing import (
    PlanInfo,
    SubscriptionResponse,
    UsageResponse,
)
from app.services.usage import current_period, get_or_create_current_record

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> SubscriptionResponse:
    """Return current subscription plan and monthly usage for the organization.

    Args:
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Subscription details including plan, usage count, and limit.
    """
    org_id = user.organization_id

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Count invoices created this month.
    now = datetime.now(UTC)
    invoice_count_result = await db.execute(
        select(UsageRecord.invoices_count).where(
            UsageRecord.organization_id == org_id,
            UsageRecord.period_start == now.replace(day=1).date(),
        )
    )
    monthly_usage = invoice_count_result.scalar() or 0

    plan_name = org.plan or "free"
    plan_def = get_plan(plan_name)

    return SubscriptionResponse(
        plan=plan_name,
        plan_limit=plan_def.invoice_limit,
        monthly_usage=monthly_usage,
        organization_name=org.name,
        features=[f.value for f in plan_def.features],
        subscription_status=org.subscription_status,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> UsageResponse:
    """Return current period usage details for the organization.

    Args:
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Current period usage with plan limits and feature access.
    """
    org_id = user.organization_id

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    plan_name = org.plan or "free"
    plan_def = get_plan(plan_name)

    period_start, period_end = current_period()
    record = await get_or_create_current_record(db, org_id)
    await db.commit()

    invoices_remaining = None
    if plan_def.invoice_limit is not None:
        invoices_remaining = max(0, plan_def.invoice_limit - record.invoices_count)

    plan_info = PlanInfo(
        tier=plan_def.tier.value,
        display_name=plan_def.display_name,
        price_monthly_eur=(
            float(plan_def.price_monthly_eur) if plan_def.price_monthly_eur is not None else None
        ),
        invoice_limit=plan_def.invoice_limit,
        user_limit=plan_def.user_limit,
        overage_per_invoice_eur=(
            float(plan_def.overage_per_invoice_eur)
            if plan_def.overage_per_invoice_eur is not None
            else None
        ),
        features=[f.value for f in plan_def.features],
    )

    return UsageResponse(
        plan=plan_info,
        period_start=period_start,
        period_end=period_end,
        invoices_used=record.invoices_count,
        invoices_limit=plan_def.invoice_limit,
        invoices_remaining=invoices_remaining,
        api_calls=record.api_calls_count,
        storage_bytes=record.storage_bytes,
        organization_name=org.name,
    )
