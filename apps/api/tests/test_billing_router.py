"""
Tests for the billing router (GET /config, GET /subscription, GET /usage,
POST /checkout, POST /cancel).

External Paddle SDK calls are fully mocked — no live Paddle API is needed.
"""

from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _auth_headers(
    client: AsyncClient,
    test_engine,
    email: str = "bill-default@example.com",
    org_name: str = "BillingOrg",
    plan: str = "agency",
) -> dict[str, str]:
    """Register user, create org, upgrade plan, return auth headers.

    Args:
        client: HTTP test client.
        test_engine: SQLAlchemy async engine for direct DB writes.
        email: User e-mail address.
        org_name: Organization name.
        plan: Plan tier to upgrade the org to.

    Returns:
        Dict with Authorization header.
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "T",
            "last_name": "U",
        },
    )
    tk = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {tk}"},
    )
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        await db.execute(
            text(f"UPDATE organizations SET plan = '{plan}' WHERE name = '{org_name}'")
        )
        await db.commit()
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


# ── GET /billing/config ────────────────────────────────────────────────────────


async def test_get_billing_config_no_auth(client: AsyncClient):
    """GET /config returns 200 without authentication."""
    resp = await client.get("/api/v1/billing/config")
    assert resp.status_code == 200


async def test_get_billing_config_shape(client: AsyncClient):
    """GET /config returns paddle_environment, paddle_client_token, and prices."""
    resp = await client.get("/api/v1/billing/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "paddle_environment" in data
    assert "paddle_client_token" in data
    assert "prices" in data
    prices = data["prices"]
    expected_keys = {
        "starter_monthly",
        "starter_annual",
        "pro_monthly",
        "pro_annual",
        "agency_monthly",
        "agency_annual",
    }
    assert set(prices.keys()) == expected_keys


# ── GET /billing/subscription ──────────────────────────────────────────────────


async def test_get_subscription_requires_auth(client: AsyncClient):
    """GET /subscription without token returns 401."""
    resp = await client.get("/api/v1/billing/subscription")
    assert resp.status_code == 401


async def test_get_subscription_success(client: AsyncClient, test_engine):
    """GET /subscription returns plan, usage, org name, and features."""
    headers = await _auth_headers(
        client, test_engine, email="bill-sub@example.com", org_name="SubOrg"
    )
    resp = await client.get("/api/v1/billing/subscription", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "agency"
    assert data["organization_name"] == "SubOrg"
    assert isinstance(data["monthly_usage"], int)
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0


async def test_get_subscription_free_plan(client: AsyncClient, test_engine):
    """GET /subscription on free plan returns correct limit and features."""
    headers = await _auth_headers(
        client,
        test_engine,
        email="bill-free@example.com",
        org_name="FreeOrg",
        plan="free",
    )
    resp = await client.get("/api/v1/billing/subscription", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["plan_limit"] == 10


async def test_get_subscription_starter_plan(client: AsyncClient, test_engine):
    """GET /subscription on starter plan returns 100 invoice limit."""
    headers = await _auth_headers(
        client,
        test_engine,
        email="bill-starter@example.com",
        org_name="StarterOrg",
        plan="starter",
    )
    resp = await client.get("/api/v1/billing/subscription", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "starter"
    assert data["plan_limit"] == 100


async def test_get_subscription_agency_unlimited_features(client: AsyncClient, test_engine):
    """Agency plan includes client_management and automation_rules features."""
    headers = await _auth_headers(
        client, test_engine, email="bill-agency@example.com", org_name="AgencyOrg"
    )
    resp = await client.get("/api/v1/billing/subscription", headers=headers)
    assert resp.status_code == 200
    features = resp.json()["features"]
    assert "client_management" in features
    assert "automation_rules" in features


# ── GET /billing/usage ─────────────────────────────────────────────────────────


async def test_get_usage_requires_auth(client: AsyncClient):
    """GET /usage without token returns 401."""
    resp = await client.get("/api/v1/billing/usage")
    assert resp.status_code == 401


async def test_get_usage_success(client: AsyncClient, test_engine):
    """GET /usage returns current period usage with plan details."""
    headers = await _auth_headers(
        client, test_engine, email="bill-usage@example.com", org_name="UsageOrg"
    )
    resp = await client.get("/api/v1/billing/usage", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    assert "period_start" in data
    assert "period_end" in data
    assert "invoices_used" in data
    assert "invoices_limit" in data
    assert "api_calls" in data
    assert "storage_bytes" in data
    assert "organization_name" in data


async def test_get_usage_plan_info_fields(client: AsyncClient, test_engine):
    """GET /usage plan object contains all required fields."""
    headers = await _auth_headers(
        client, test_engine, email="bill-usage2@example.com", org_name="UsageOrg2"
    )
    resp = await client.get("/api/v1/billing/usage", headers=headers)
    assert resp.status_code == 200
    plan = resp.json()["plan"]
    assert plan["tier"] == "agency"
    assert plan["display_name"] == "Agency"
    assert plan["invoice_limit"] == 1500
    assert plan["user_limit"] == 15
    assert isinstance(plan["features"], list)


async def test_get_usage_free_plan_has_remaining(client: AsyncClient, test_engine):
    """GET /usage on free plan returns non-null invoices_remaining."""
    headers = await _auth_headers(
        client,
        test_engine,
        email="bill-usage3@example.com",
        org_name="UsageOrg3",
        plan="free",
    )
    resp = await client.get("/api/v1/billing/usage", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["invoices_remaining"] is not None
    assert data["invoices_remaining"] >= 0


async def test_get_usage_period_dates_valid(client: AsyncClient, test_engine):
    """GET /usage period_start is before period_end."""
    headers = await _auth_headers(
        client, test_engine, email="bill-dates@example.com", org_name="DatesOrg"
    )
    resp = await client.get("/api/v1/billing/usage", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    from datetime import date

    start = date.fromisoformat(data["period_start"])
    end = date.fromisoformat(data["period_end"])
    assert start < end
    assert start.day == 1


# ── POST /billing/checkout ─────────────────────────────────────────────────────


async def test_checkout_requires_auth(client: AsyncClient):
    """POST /checkout without token returns 401."""
    resp = await client.post(
        "/api/v1/billing/checkout", json={"tier": "starter", "interval": "monthly"}
    )
    assert resp.status_code == 401


async def test_checkout_invalid_tier(client: AsyncClient, test_engine):
    """POST /checkout with unknown tier returns 400."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co1@example.com", org_name="CheckoutOrg1"
    )
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "ultraplan", "interval": "monthly"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_checkout_free_tier_rejected(client: AsyncClient, test_engine):
    """POST /checkout for free tier returns 400."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co2@example.com", org_name="CheckoutOrg2"
    )
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "free", "interval": "monthly"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "free plan" in resp.json()["detail"].lower()


async def test_checkout_invalid_interval(client: AsyncClient, test_engine):
    """POST /checkout with invalid interval returns 400."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co3@example.com", org_name="CheckoutOrg3"
    )
    resp = await client.post(
        "/api/v1/billing/checkout",
        json={"tier": "starter", "interval": "weekly"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "interval" in resp.json()["detail"].lower()


async def test_checkout_success_with_mocked_price(client: AsyncClient, test_engine):
    """POST /checkout returns price_id and custom_data when price is configured."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co4@example.com", org_name="CheckoutOrg4"
    )
    with patch("app.services.paddle.get_price_id", return_value="pri_mock_starter_monthly"):
        resp = await client.post(
            "/api/v1/billing/checkout",
            json={"tier": "starter", "interval": "monthly"},
            headers=headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["price_id"] == "pri_mock_starter_monthly"
    assert "organization_id" in data["custom_data"]


async def test_checkout_no_price_configured_returns_400(client: AsyncClient, test_engine):
    """POST /checkout returns 400 when no Paddle price is configured for tier."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co5@example.com", org_name="CheckoutOrg5"
    )
    with patch("app.services.paddle.get_price_id", return_value=None):
        resp = await client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "interval": "annual"},
            headers=headers,
        )
    assert resp.status_code == 400


async def test_checkout_includes_customer_email(client: AsyncClient, test_engine):
    """POST /checkout response includes customer_email from org billing email or user email."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co6@example.com", org_name="CheckoutOrg6"
    )
    with patch("app.services.paddle.get_price_id", return_value="pri_mock_agency"):
        resp = await client.post(
            "/api/v1/billing/checkout",
            json={"tier": "agency", "interval": "monthly"},
            headers=headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    # customer_email is optional but if present must be a string
    if data.get("customer_email") is not None:
        assert isinstance(data["customer_email"], str)


async def test_checkout_annual_interval_accepted(client: AsyncClient, test_engine):
    """POST /checkout accepts annual interval."""
    headers = await _auth_headers(
        client, test_engine, email="bill-co7@example.com", org_name="CheckoutOrg7"
    )
    with patch("app.services.paddle.get_price_id", return_value="pri_mock_pro_annual"):
        resp = await client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "interval": "annual"},
            headers=headers,
        )
    assert resp.status_code == 200
    assert resp.json()["price_id"] == "pri_mock_pro_annual"


# ── POST /billing/cancel ───────────────────────────────────────────────────────


async def test_cancel_requires_auth(client: AsyncClient):
    """POST /cancel without token returns 401."""
    resp = await client.post("/api/v1/billing/cancel")
    assert resp.status_code == 401


async def test_cancel_no_subscription_returns_400(client: AsyncClient, test_engine):
    """POST /cancel when org has no subscription returns 400."""
    headers = await _auth_headers(
        client, test_engine, email="bill-cancel1@example.com", org_name="CancelOrg1"
    )
    resp = await client.post("/api/v1/billing/cancel", headers=headers)
    assert resp.status_code == 400
    assert "subscription" in resp.json()["detail"].lower()


async def test_cancel_no_paddle_key_returns_503(client: AsyncClient, test_engine):
    """POST /cancel when Paddle is not configured returns 503."""
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    headers = await _auth_headers(
        client, test_engine, email="bill-cancel2@example.com", org_name="CancelOrg2"
    )
    # Inject a subscription ID so the org check passes
    async with sf() as db:
        await db.execute(
            text(
                "UPDATE organizations "
                "SET payment_provider_subscription_id = 'sub_test_123' "
                "WHERE name = 'CancelOrg2'"
            )
        )
        await db.commit()

    with patch("app.routers.billing.settings") as mock_settings:
        mock_settings.paddle_api_key = None
        mock_settings.paddle_environment = "sandbox"
        resp = await client.post("/api/v1/billing/cancel", headers=headers)
    assert resp.status_code == 503


async def test_cancel_success_mocked_paddle(client: AsyncClient, test_engine):
    """POST /cancel calls Paddle SDK and returns cancellation_requested."""
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    headers = await _auth_headers(
        client, test_engine, email="bill-cancel3@example.com", org_name="CancelOrg3"
    )
    async with sf() as db:
        await db.execute(
            text(
                "UPDATE organizations "
                "SET payment_provider_subscription_id = 'sub_test_456' "
                "WHERE name = 'CancelOrg3'"
            )
        )
        await db.commit()

    mock_paddle_client = MagicMock()
    mock_paddle_client.subscriptions.cancel = MagicMock(return_value=None)

    with (
        patch("app.routers.billing.settings") as mock_settings,
        patch("paddle_billing.Client", return_value=mock_paddle_client),
    ):
        mock_settings.paddle_api_key = "test_api_key"
        mock_settings.paddle_environment = "sandbox"
        resp = await client.post("/api/v1/billing/cancel", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancellation_requested"


async def test_cancel_paddle_error_returns_502(client: AsyncClient, test_engine):
    """POST /cancel returns 502 when Paddle SDK raises an exception."""
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    headers = await _auth_headers(
        client, test_engine, email="bill-cancel4@example.com", org_name="CancelOrg4"
    )
    async with sf() as db:
        await db.execute(
            text(
                "UPDATE organizations "
                "SET payment_provider_subscription_id = 'sub_test_789' "
                "WHERE name = 'CancelOrg4'"
            )
        )
        await db.commit()

    def _raise(*args, **kwargs):
        raise RuntimeError("Paddle API error")

    mock_paddle_client = MagicMock()
    mock_paddle_client.subscriptions.cancel = _raise

    with (
        patch("app.routers.billing.settings") as mock_settings,
        patch("paddle_billing.Client", return_value=mock_paddle_client),
    ):
        mock_settings.paddle_api_key = "test_api_key"
        mock_settings.paddle_environment = "sandbox"
        resp = await client.post("/api/v1/billing/cancel", headers=headers)

    assert resp.status_code == 502
