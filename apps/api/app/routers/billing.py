"""Billing router — subscription info, usage stats, and Paddle checkout."""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User
from app.plans import PlanTier, get_plan
from app.schemas.billing import (
    BillingConfigResponse,
    CheckoutRequest,
    CheckoutResponse,
    PlanInfo,
    SubscriptionResponse,
    UsageResponse,
)
from app.services.paddle import get_checkout_settings
from app.services.usage import current_period, get_or_create_current_record

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/config", response_model=BillingConfigResponse)
async def get_billing_config() -> BillingConfigResponse:
    """Return public Paddle configuration for frontend initialization.

    No authentication required — these are client-side tokens.

    Returns:
        Paddle environment, client token, and price ID mapping.
    """
    return BillingConfigResponse(
        paddle_environment=settings.paddle_environment,
        paddle_client_token=settings.paddle_client_side_token,
        prices={
            "starter_monthly": settings.paddle_price_id_starter_monthly or None,
            "starter_annual": settings.paddle_price_id_starter_annual or None,
            "pro_monthly": settings.paddle_price_id_pro_monthly or None,
            "pro_annual": settings.paddle_price_id_pro_annual or None,
            "agency_monthly": settings.paddle_price_id_agency_monthly or None,
            "agency_annual": settings.paddle_price_id_agency_annual or None,
        },
    )


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
        select(func.count())
        .select_from(Invoice)
        .where(
            Invoice.organization_id == org_id,
            extract("year", Invoice.created_at) == now.year,
            extract("month", Invoice.created_at) == now.month,
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
        paddle_customer_id=org.payment_provider_customer_id,
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
            float(plan_def.price_monthly_eur)
            if plan_def.price_monthly_eur is not None
            else None
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


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> CheckoutResponse:
    """Generate checkout settings for Paddle.js overlay.

    Args:
        body: Target plan tier and billing interval.
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Price ID and customer info for Paddle.Checkout.open().
    """
    try:
        tier = PlanTier(body.tier)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {body.tier}",
        )

    if tier == PlanTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout for free plan",
        )

    if body.interval not in ("monthly", "annual"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interval must be 'monthly' or 'annual'",
        )

    result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    try:
        checkout = get_checkout_settings(
            tier=tier,
            interval=body.interval,
            org_id=str(org.id),
            billing_email=org.billing_email or user.email,
            paddle_customer_id=org.payment_provider_customer_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return CheckoutResponse(**checkout)


@router.post("/cancel")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Request subscription cancellation via Paddle API.

    Args:
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Confirmation dict.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org or not org.payment_provider_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription",
        )

    if not settings.paddle_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paddle is not configured",
        )

    from paddle_billing import Client, Environment, Options

    env = (
        Environment.SANDBOX
        if settings.paddle_environment == "sandbox"
        else Environment.PRODUCTION
    )
    paddle = Client(settings.paddle_api_key, options=Options(env))

    try:
        await asyncio.to_thread(
            paddle.subscriptions.cancel,
            org.payment_provider_subscription_id,
        )
    except Exception:
        logger.exception("Failed to cancel Paddle subscription")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to cancel subscription",
        )

    return {"status": "cancellation_requested"}
