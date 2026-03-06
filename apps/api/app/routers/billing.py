"""Billing router — subscription info and usage stats."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User
from app.schemas.billing import SubscriptionResponse

router = APIRouter()

# Plan limits configuration (invoices per month).
PLAN_LIMITS: dict[str, int | None] = {
    "free": 10,
    "starter": 100,
    "professional": 500,
    "enterprise": None,
}


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Return current subscription plan and monthly usage for the organization.

    Args:
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Subscription details including plan, usage count, and limit.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view billing information",
        )

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
        select(func.count())
        .select_from(Invoice)
        .where(
            Invoice.organization_id == org_id,
            extract("year", Invoice.created_at) == now.year,
            extract("month", Invoice.created_at) == now.month,
        )
    )
    monthly_usage = invoice_count_result.scalar() or 0

    plan = org.plan or "free"
    plan_limit = PLAN_LIMITS.get(plan)

    return SubscriptionResponse(
        plan=plan,
        plan_limit=plan_limit,
        monthly_usage=monthly_usage,
        organization_name=org.name,
    )
