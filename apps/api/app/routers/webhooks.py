"""Webhook router — external integration endpoints."""

import logging

from fastapi import APIRouter, Request

router = APIRouter()
logger = logging.getLogger(__name__)


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
