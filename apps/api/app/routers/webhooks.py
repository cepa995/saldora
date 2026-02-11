"""Webhook router - Stripe and other integrations."""

from fastapi import APIRouter, Header, Request

from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
) -> dict[str, str]:
    """
    Handle Stripe webhook events.

    Processes subscription lifecycle events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - invoice.payment_failed
    """
    # TODO: Implement Stripe webhook handling
    # 1. Verify webhook signature
    # 2. Parse event type
    # 3. Handle event based on type
    # 4. Update organization subscription status
    # 5. Send notification emails if needed

    _body = await request.body()  # noqa: F841 - will be used when Stripe is enabled

    # Verify signature
    # import stripe
    # try:
    #     event = stripe.Webhook.construct_event(
    #         body, stripe_signature, settings.stripe_webhook_secret
    #     )
    # except ValueError:
    #     raise HTTPException(status_code=400, detail="Invalid payload")
    # except stripe.error.SignatureVerificationError:
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    return {"status": "received"}


@router.post("/apr")
async def apr_webhook(request: Request) -> dict[str, str]:
    """
    Handle APR data update notifications (if available).

    Updates cached company information when APR notifies
    of changes to registered businesses.
    """
    # APR may not have webhooks, but this is a placeholder
    # for future integration if they add this capability
    return {"status": "received"}


@router.get("/test")
async def test_webhook() -> dict[str, str]:
    """
    Test endpoint for webhook configuration verification.
    """
    return {"status": "ok", "message": "Webhook endpoint is reachable"}
