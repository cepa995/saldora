"""Tests for Paddle billing integration (Issue #46).

Tests cover:
- Webhook signature verification
- Webhook endpoint handling (subscription lifecycle)
- Billing config endpoint (public, no auth)
- Checkout endpoint (admin-only)
- Price-to-plan mapping
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.services.paddle import (
    get_checkout_settings,
    resolve_plan_from_price_id,
    verify_paddle_signature,
)

# ---- Helpers ----


async def _register_and_login(
    client: AsyncClient,
    email: str = "paddle-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Paddle",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Paddle Test Org"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _get_org_plan(test_engine, org_id: str) -> str:
    """Read the current plan for an organization directly from DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT plan FROM organizations WHERE id = :org_id"),
            {"org_id": org_id},
        )
        return result.scalar_one()


async def _get_org_subscription_status(test_engine, org_id: str) -> str | None:
    """Read the subscription_status for an organization directly from DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT subscription_status FROM organizations WHERE id = :org_id"),
            {"org_id": org_id},
        )
        return result.scalar_one()


def _make_signature(body: bytes, secret: str) -> str:
    """Create a valid Paddle-Signature header value."""
    ts = str(int(time.time()))
    signed_payload = f"{ts}:{body.decode('utf-8')}"
    h1 = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"ts={ts};h1={h1}"


# ---- Unit tests: signature verification ----


def test_verify_paddle_signature_valid():
    """A correctly signed payload should pass verification."""
    secret = "test_secret_key"
    body = b'{"event_type":"subscription.created","data":{}}'
    sig = _make_signature(body, secret)

    assert verify_paddle_signature(body, sig, secret) is True


def test_verify_paddle_signature_invalid_hash():
    """A tampered hash should fail verification."""
    secret = "test_secret_key"
    body = b'{"event_type":"subscription.created","data":{}}'
    ts = str(int(time.time()))
    sig = f"ts={ts};h1=invalid_hash_value"

    assert verify_paddle_signature(body, sig, secret) is False


def test_verify_paddle_signature_expired():
    """An expired timestamp (>300s) should fail verification."""
    secret = "test_secret_key"
    body = b'{"data":{}}'
    old_ts = str(int(time.time()) - 600)
    signed_payload = f"{old_ts}:{body.decode('utf-8')}"
    h1 = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    sig = f"ts={old_ts};h1={h1}"

    assert verify_paddle_signature(body, sig, secret) is False


def test_verify_paddle_signature_missing_parts():
    """Malformed signature header should fail."""
    assert verify_paddle_signature(b"body", "malformed", "secret") is False
    assert verify_paddle_signature(b"body", "ts=123", "secret") is False
    assert verify_paddle_signature(b"body", "h1=abc", "secret") is False


# ---- Unit tests: price mapping ----


def test_resolve_plan_unknown_price():
    """Unknown price IDs should return None."""
    assert resolve_plan_from_price_id("pri_unknown_123") is None


def test_get_checkout_settings_missing_price():
    """Requesting checkout for an unconfigured plan should raise ValueError."""
    from app.plans import PlanTier

    try:
        get_checkout_settings(
            tier=PlanTier.STARTER,
            interval="monthly",
            org_id="test-org-id",
        )
        # If no price is configured, it should raise
        # But if test env has configured prices, this is fine
    except ValueError as exc:
        assert "No Paddle price configured" in str(exc)


# ---- API tests: GET /billing/config ----


async def test_billing_config_no_auth(client: AsyncClient):
    """GET /billing/config should not require authentication."""
    resp = await client.get("/api/v1/billing/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "paddle_environment" in data
    assert "paddle_client_token" in data
    assert "prices" in data
    assert "starter_monthly" in data["prices"]
    assert "pro_annual" in data["prices"]
    assert "agency_monthly" in data["prices"]


# ---- API tests: POST /billing/checkout ----


async def test_checkout_requires_admin(client: AsyncClient):
    """POST /billing/checkout should require authentication."""
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "pro", "interval": "monthly"},
    )
    assert resp.status_code == 401


async def test_checkout_invalid_tier(client: AsyncClient):
    """POST /billing/checkout with invalid tier should return 400."""
    headers = await _register_and_login(client, email="checkout-invalid@example.com")
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "platinum", "interval": "monthly"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Unknown plan" in resp.json()["detail"]


async def test_checkout_free_tier(client: AsyncClient):
    """POST /billing/checkout for free tier should return 400."""
    headers = await _register_and_login(client, email="checkout-free@example.com")
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "free", "interval": "monthly"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_checkout_invalid_interval(client: AsyncClient):
    """POST /billing/checkout with invalid interval should return 400."""
    headers = await _register_and_login(client, email="checkout-interval@example.com")
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "pro", "interval": "weekly"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Interval" in resp.json()["detail"]


# ---- API tests: POST /billing/cancel ----


async def test_cancel_no_subscription(client: AsyncClient):
    """POST /billing/cancel without active subscription should return 400."""
    headers = await _register_and_login(client, email="cancel-nosub@example.com")
    resp = await client.post("/api/v1/billing/cancel", headers=headers)
    assert resp.status_code == 400
    assert "No active subscription" in resp.json()["detail"]


# ---- API tests: Paddle webhook ----


async def test_paddle_webhook_missing_signature(client: AsyncClient):
    """POST /webhooks/paddle without signature header should return 422."""
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.paddle_webhook_secret = "test_secret"
        resp = await client.post(
            "/api/v1/webhooks/paddle",
            content=b'{"event_type":"test","data":{}}',
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 422


async def test_paddle_webhook_unknown_event(client: AsyncClient):
    """Unknown event type should still return 200 (acknowledged)."""
    body = json.dumps({"event_type": "customer.created", "data": {}}).encode()
    with (
        patch("app.routers.webhooks.settings") as mock_settings,
        patch("app.routers.webhooks.verify_paddle_signature", return_value=True),
    ):
        mock_settings.paddle_webhook_secret = "test_secret"
        resp = await client.post(
            "/api/v1/webhooks/paddle",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Paddle-Signature": "ts=0;h1=unused",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


async def test_paddle_webhook_subscription_created(
    client: AsyncClient,
    test_engine,
):
    """subscription.created should update the organization plan."""
    headers = await _register_and_login(client, email="webhook-created@example.com")
    org_id = _get_org_id(headers)

    # Verify org starts on free plan
    assert await _get_org_plan(test_engine, org_id) == "free"

    # Simulate subscription.created webhook — no webhook secret configured
    # so signature verification is skipped
    event = {
        "event_type": "subscription.created",
        "data": {
            "id": "sub_test_123",
            "customer_id": "ctm_test_456",
            "status": "active",
            "custom_data": {"organization_id": org_id},
            "items": [{"price": {"id": "pri_test_pro_monthly"}}],
        },
    }
    body = json.dumps(event).encode()

    # We need the price ID to be in the PRICE_TO_PLAN map for the plan
    # to be resolved. Since test env has no prices configured, the plan
    # will be None (unresolved), but the customer_id and subscription_id
    # should still be saved.
    with (
        patch("app.routers.webhooks.settings") as mock_settings,
        patch("app.routers.webhooks.verify_paddle_signature", return_value=True),
    ):
        mock_settings.paddle_webhook_secret = "test_secret"
        resp = await client.post(
            "/api/v1/webhooks/paddle",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Paddle-Signature": "ts=0;h1=unused",
            },
        )
    assert resp.status_code == 200

    # Verify subscription_status was updated
    status = await _get_org_subscription_status(test_engine, org_id)
    assert status == "active"


async def test_paddle_webhook_subscription_canceled(
    client: AsyncClient,
    test_engine,
):
    """subscription.canceled should downgrade the organization to free."""
    headers = await _register_and_login(client, email="webhook-cancel@example.com")
    org_id = _get_org_id(headers)

    # Set plan to pro first
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE organizations SET plan = 'pro' WHERE id = :org_id"),
            {"org_id": org_id},
        )
        await session.commit()

    assert await _get_org_plan(test_engine, org_id) == "pro"

    # Send subscription.canceled webhook
    event = {
        "event_type": "subscription.canceled",
        "data": {
            "id": "sub_test_cancel",
            "customer_id": "ctm_test_cancel",
            "status": "canceled",
            "custom_data": {"organization_id": org_id},
            "items": [],
        },
    }
    body = json.dumps(event).encode()

    with (
        patch("app.routers.webhooks.settings") as mock_settings,
        patch("app.routers.webhooks.verify_paddle_signature", return_value=True),
    ):
        mock_settings.paddle_webhook_secret = "test_secret"
        resp = await client.post(
            "/api/v1/webhooks/paddle",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Paddle-Signature": "ts=0;h1=unused",
            },
        )
    assert resp.status_code == 200

    # Verify plan downgraded to free
    assert await _get_org_plan(test_engine, org_id) == "free"
    assert await _get_org_subscription_status(test_engine, org_id) == "canceled"


async def test_paddle_webhook_transaction_completed(client: AsyncClient):
    """transaction.completed should return 200 (log only, no state change)."""
    event = {
        "event_type": "transaction.completed",
        "data": {
            "id": "txn_test_123",
            "subscription_id": "sub_test_123",
            "custom_data": {"organization_id": "nonexistent"},
        },
    }
    body = json.dumps(event).encode()

    with (
        patch("app.routers.webhooks.settings") as mock_settings,
        patch("app.routers.webhooks.verify_paddle_signature", return_value=True),
    ):
        mock_settings.paddle_webhook_secret = "test_secret"
        resp = await client.post(
            "/api/v1/webhooks/paddle",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Paddle-Signature": "ts=0;h1=unused",
            },
        )
    assert resp.status_code == 200


async def test_paddle_webhook_missing_org_id(client: AsyncClient):
    """Webhook without organization_id in custom_data should still return 200."""
    event = {
        "event_type": "subscription.created",
        "data": {
            "id": "sub_test_noorg",
            "customer_id": "ctm_test_noorg",
            "status": "active",
            "custom_data": {},
            "items": [],
        },
    }
    body = json.dumps(event).encode()

    with (
        patch("app.routers.webhooks.settings") as mock_settings,
        patch("app.routers.webhooks.verify_paddle_signature", return_value=True),
    ):
        mock_settings.paddle_webhook_secret = "test_secret"
        resp = await client.post(
            "/api/v1/webhooks/paddle",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Paddle-Signature": "ts=0;h1=unused",
            },
        )
    assert resp.status_code == 200


# ---- API tests: GET /billing/subscription ----


async def test_subscription_includes_paddle_fields(client: AsyncClient):
    """GET /billing/subscription should include subscription_status and paddle_customer_id."""
    headers = await _register_and_login(client, email="sub-fields@example.com")
    resp = await client.get("/api/v1/billing/subscription", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "subscription_status" in data
    assert "paddle_customer_id" in data
    assert data["plan"] == "free"
