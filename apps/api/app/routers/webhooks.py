"""Webhook router — Paddle Billing and other integrations."""

import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.paddle import WEBHOOK_HANDLERS, verify_paddle_signature

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/paddle")
async def paddle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    paddle_signature: str = Header(alias="Paddle-Signature"),
) -> dict[str, str]:
    """Handle Paddle Billing webhook events.

    Verifies the webhook signature, then dispatches to the appropriate
    handler based on event type.

    Processes subscription lifecycle events:
    - subscription.created / subscription.activated
    - subscription.updated
    - subscription.canceled
    - transaction.completed
    - transaction.payment_failed

    Args:
        request: Raw HTTP request (need body bytes for signature verification).
        paddle_signature: Paddle-Signature header value.

    Returns:
        Acknowledgement dict.
    """
    raw_body = await request.body()

    # Verify webhook signature
    if settings.paddle_webhook_secret:
        if not verify_paddle_signature(raw_body, paddle_signature, settings.paddle_webhook_secret):
            logger.warning("Paddle webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")

    # Parse event
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event_type", "")
    data = payload.get("data", {})

    handler = WEBHOOK_HANDLERS.get(event_type)
    if handler:
        try:
            await handler(db, data)
        except Exception:
            logger.exception("Error handling Paddle event: %s", event_type)
            raise HTTPException(status_code=500, detail="Webhook processing error")
    else:
        logger.debug("Unhandled Paddle event type: %s", event_type)

    return {"status": "received"}


@router.post("/apr")
async def apr_webhook(request: Request) -> dict[str, str]:
    """Handle APR data update notifications (if available).

    Updates cached company information when APR notifies
    of changes to registered businesses.

    Args:
        request: Raw HTTP request.

    Returns:
        Acknowledgement dict.
    """
    # APR may not have webhooks, but this is a placeholder
    # for future integration if they add this capability
    return {"status": "received"}


@router.get("/test")
async def test_webhook() -> dict[str, str]:
    """Test endpoint for webhook configuration verification.

    Returns:
        Status dict.
    """
    return {"status": "ok", "message": "Webhook endpoint is reachable"}
