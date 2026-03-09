"""Paddle Billing integration service.

Handles checkout settings generation, price-to-plan mapping,
webhook signature verification, and subscription lifecycle event processing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.organization import Organization
from app.plans import PlanTier

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Price mapping ────────────────────────────────────────────────────


def _build_price_map() -> dict[str, tuple[PlanTier, str]]:
    """Build a mapping from Paddle price_id to (PlanTier, interval).

    Returns:
        Dict mapping paddle price_id -> (PlanTier, "monthly"|"annual").
    """
    mapping: dict[str, tuple[PlanTier, str]] = {}
    pairs = [
        (settings.paddle_price_id_starter_monthly, PlanTier.STARTER, "monthly"),
        (settings.paddle_price_id_starter_annual, PlanTier.STARTER, "annual"),
        (settings.paddle_price_id_pro_monthly, PlanTier.PRO, "monthly"),
        (settings.paddle_price_id_pro_annual, PlanTier.PRO, "annual"),
        (settings.paddle_price_id_agency_monthly, PlanTier.AGENCY, "monthly"),
        (settings.paddle_price_id_agency_annual, PlanTier.AGENCY, "annual"),
    ]
    for price_id, tier, interval in pairs:
        if price_id:
            mapping[price_id] = (tier, interval)
    return mapping


PRICE_TO_PLAN = _build_price_map()


def get_price_id(tier: PlanTier, interval: str) -> str | None:
    """Look up the Paddle price_id for a given plan tier and interval.

    Args:
        tier: Target plan tier.
        interval: "monthly" or "annual".

    Returns:
        Paddle price ID string, or None if not configured.
    """
    attr = f"paddle_price_id_{tier.value}_{interval}"
    value = getattr(settings, attr, None)
    return value or None


def resolve_plan_from_price_id(price_id: str) -> tuple[PlanTier, str] | None:
    """Map a Paddle price_id back to a PlanTier and billing interval.

    Args:
        price_id: Paddle price identifier.

    Returns:
        Tuple of (PlanTier, interval) or None if unknown.
    """
    return PRICE_TO_PLAN.get(price_id)


# ── Checkout settings ────────────────────────────────────────────────


def get_checkout_settings(
    tier: PlanTier,
    interval: str,
    org_id: str,
    billing_email: str | None = None,
    paddle_customer_id: str | None = None,
) -> dict:
    """Build checkout settings for Paddle.js overlay.

    Args:
        tier: Target plan tier.
        interval: "monthly" or "annual".
        org_id: Organization UUID string (passed as custom_data).
        billing_email: Pre-fill customer email if known.
        paddle_customer_id: Existing Paddle customer ID for returning customers.

    Returns:
        Dict with price_id, custom_data, and optional customer info.

    Raises:
        ValueError: If no Paddle price is configured for the tier/interval.
    """
    price_id = get_price_id(tier, interval)
    if not price_id:
        raise ValueError(f"No Paddle price configured for {tier.value}/{interval}")

    result: dict = {
        "price_id": price_id,
        "custom_data": {"organization_id": str(org_id)},
    }

    if billing_email:
        result["customer_email"] = billing_email
    if paddle_customer_id:
        result["customer_id"] = paddle_customer_id

    return result


# ── Webhook signature verification ───────────────────────────────────


def verify_paddle_signature(
    raw_body: bytes,
    signature_header: str,
    secret: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify a Paddle webhook signature (HMAC-SHA256).

    Paddle sends a `Paddle-Signature` header with format `ts=<timestamp>;h1=<hash>`.
    We reconstruct the signed payload as `ts:body` and compare HMAC digests.

    Args:
        raw_body: Raw request body bytes.
        signature_header: Value of the Paddle-Signature header.
        secret: Paddle webhook secret key.
        max_age_seconds: Maximum allowed age of the signature in seconds.

    Returns:
        True if signature is valid and not expired.
    """
    parts: dict[str, str] = {}
    for pair in signature_header.split(";"):
        key, _, value = pair.partition("=")
        parts[key.strip()] = value.strip()

    ts = parts.get("ts", "")
    h1 = parts.get("h1", "")

    if not ts or not h1:
        return False

    # Check timestamp drift
    try:
        if abs(time.time() - int(ts)) > max_age_seconds:
            return False
    except ValueError:
        return False

    signed_payload = f"{ts}:{raw_body.decode('utf-8')}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, h1)


# ── Webhook event handlers ───────────────────────────────────────────


async def handle_subscription_created(
    db: AsyncSession,
    data: dict,
) -> None:
    """Process subscription.created / subscription.activated webhook event.

    Args:
        db: Database session.
        data: Paddle event data payload.
    """
    org_id = _extract_org_id(data)
    if not org_id:
        logger.warning("subscription.created missing organization_id in custom_data")
        return

    subscription_id = data.get("id")
    customer_id = data.get("customer_id")
    items = data.get("items", [])
    price_id = items[0]["price"]["id"] if items else None

    plan_info = resolve_plan_from_price_id(price_id) if price_id else None
    new_tier = plan_info[0].value if plan_info else None

    await _update_org_subscription(
        db,
        org_id=org_id,
        customer_id=customer_id,
        subscription_id=subscription_id,
        plan=new_tier,
        subscription_status="active",
    )
    logger.info("subscription.created: org=%s plan=%s", org_id, new_tier)


async def handle_subscription_updated(
    db: AsyncSession,
    data: dict,
) -> None:
    """Process subscription.updated webhook event (plan changes, pauses, resumes).

    Args:
        db: Database session.
        data: Paddle event data payload.
    """
    org_id = _extract_org_id(data)
    if not org_id:
        logger.warning("subscription.updated missing organization_id in custom_data")
        return

    items = data.get("items", [])
    price_id = items[0]["price"]["id"] if items else None
    paddle_status = data.get("status")  # active, paused, past_due, canceled

    plan_info = resolve_plan_from_price_id(price_id) if price_id else None
    new_tier = plan_info[0].value if plan_info else None

    await _update_org_subscription(
        db,
        org_id=org_id,
        plan=new_tier,
        subscription_status=paddle_status,
    )
    logger.info(
        "subscription.updated: org=%s plan=%s status=%s",
        org_id,
        new_tier,
        paddle_status,
    )


async def handle_subscription_canceled(
    db: AsyncSession,
    data: dict,
) -> None:
    """Process subscription.canceled webhook event.

    Args:
        db: Database session.
        data: Paddle event data payload.
    """
    org_id = _extract_org_id(data)
    if not org_id:
        logger.warning("subscription.canceled missing organization_id in custom_data")
        return

    await _update_org_subscription(
        db,
        org_id=org_id,
        plan="free",
        subscription_status="canceled",
    )
    logger.info("subscription.canceled: org=%s downgraded to free", org_id)


async def handle_transaction_completed(
    db: AsyncSession,
    data: dict,
) -> None:
    """Process transaction.completed webhook event (payment success).

    Args:
        db: Database session.
        data: Paddle event data payload.
    """
    org_id = _extract_org_id(data)
    subscription_id = data.get("subscription_id")
    logger.info(
        "transaction.completed: org=%s subscription=%s",
        org_id,
        subscription_id,
    )


async def handle_transaction_payment_failed(
    db: AsyncSession,
    data: dict,
) -> None:
    """Process transaction.payment_failed webhook event.

    Paddle handles retry logic automatically. If all retries fail,
    subscription.updated will fire with status=past_due, and eventually
    subscription.canceled.

    Args:
        db: Database session.
        data: Paddle event data payload.
    """
    org_id = _extract_org_id(data)
    logger.warning("transaction.payment_failed: org=%s", org_id)


# ── Dispatch table ───────────────────────────────────────────────────

WEBHOOK_HANDLERS: dict = {
    "subscription.created": handle_subscription_created,
    "subscription.activated": handle_subscription_created,
    "subscription.updated": handle_subscription_updated,
    "subscription.canceled": handle_subscription_canceled,
    "transaction.completed": handle_transaction_completed,
    "transaction.payment_failed": handle_transaction_payment_failed,
}


# ── Internal helpers ─────────────────────────────────────────────────


def _extract_org_id(data: dict) -> str | None:
    """Extract organization_id from Paddle event custom_data.

    Args:
        data: Paddle event data payload.

    Returns:
        Organization UUID string or None.
    """
    custom_data = data.get("custom_data") or {}
    return custom_data.get("organization_id")


async def _update_org_subscription(
    db: AsyncSession,
    org_id: str,
    customer_id: str | None = None,
    subscription_id: str | None = None,
    plan: str | None = None,
    subscription_status: str | None = None,
) -> None:
    """Update an organization's subscription fields.

    Args:
        db: Database session.
        org_id: Organization UUID string.
        customer_id: Paddle customer ID.
        subscription_id: Paddle subscription ID.
        plan: New plan tier name.
        subscription_status: Paddle subscription status.
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        logger.error("Organization not found: %s", org_id)
        return

    if customer_id is not None:
        org.payment_provider_customer_id = customer_id
    if subscription_id is not None:
        org.payment_provider_subscription_id = subscription_id
    if plan is not None:
        org.plan = plan
    if subscription_status is not None:
        org.subscription_status = subscription_status

    await db.commit()
