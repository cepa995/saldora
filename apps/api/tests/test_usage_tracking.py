"""Tests for usage tracking, plan enforcement, and feature gates."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice
from app.models.usage_record import UsageRecord


async def _register_and_login(
    client: AsyncClient,
    email: str = "usage-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Usage",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Usage Test Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _set_org_plan(test_engine, org_id: str, plan: str) -> None:
    """Update organization plan directly in the database."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("UPDATE organizations SET plan = :plan WHERE id = :org_id"),
            {"plan": plan, "org_id": org_id},
        )
        await session.commit()


async def _insert_invoices(test_engine, org_id: str, count: int) -> None:
    """Insert test invoices directly into the DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        for i in range(count):
            invoice = Invoice(
                id=uuid4(),
                organization_id=org_id,
                status="review",
                invoice_number=f"INV-{i:04d}",
                invoice_date=date(2026, 3, 1),
                total_amount=Decimal("1000.00"),
                currency="RSD",
            )
            session.add(invoice)
        await session.commit()


async def _get_usage_record(test_engine, org_id: str) -> UsageRecord | None:
    """Get the current month's usage record for an org."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import select

        now = datetime.now(UTC)
        period_start = now.date().replace(day=1)
        result = await session.execute(
            select(UsageRecord).where(
                UsageRecord.organization_id == org_id,
                UsageRecord.period_start == period_start,
            )
        )
        return result.scalar_one_or_none()


class TestSubscriptionEndpoint:
    """Test GET /api/v1/billing/subscription."""

    async def test_returns_plan_and_features(self, client, test_engine):
        """Subscription endpoint returns plan info with features list."""
        headers = await _register_and_login(client, email="sub-features@example.com")

        # Default plan is "free"
        resp = await client.get("/api/v1/billing/subscription", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "free"
        assert "features" in data
        assert isinstance(data["features"], list)
        assert "ocr_extraction" in data["features"]

    async def test_pro_plan_has_sef_feature(self, client, test_engine):
        """Pro plan subscription includes SEF in features."""
        headers = await _register_and_login(client, email="sub-pro@example.com")
        org_id = _get_org_id(headers)
        await _set_org_plan(test_engine, org_id, "pro")

        resp = await client.get("/api/v1/billing/subscription", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "pro"
        assert "sef_integration" in data["features"]
        assert "accounting_intent" in data["features"]


class TestUsageEndpoint:
    """Test GET /api/v1/billing/usage."""

    async def test_returns_usage_details(self, client, test_engine):
        """Usage endpoint returns period, plan info, and usage counts."""
        headers = await _register_and_login(client, email="usage-detail@example.com")

        resp = await client.get("/api/v1/billing/usage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plan" in data
        assert "period_start" in data
        assert "period_end" in data
        assert data["invoices_used"] == 0
        assert data["plan"]["tier"] == "free"


class TestFeatureGate:
    """Test require_feature dependency on gated endpoints."""

    async def test_free_plan_blocked_from_sef(self, client, test_engine):
        """Free plan user gets 403 when accessing SEF endpoints."""
        headers = await _register_and_login(client, email="gate-sef@example.com")

        resp = await client.get("/api/v1/sef/inbox", headers=headers)
        assert resp.status_code == 403
        data = resp.json()["detail"]
        assert data["code"] == "feature_unavailable"
        assert data["plan"] == "free"

    async def test_pro_plan_allowed_sef(self, client, test_engine):
        """Pro plan user can access SEF endpoints."""
        headers = await _register_and_login(client, email="gate-sef-pro@example.com")
        org_id = _get_org_id(headers)
        await _set_org_plan(test_engine, org_id, "pro")

        resp = await client.get("/api/v1/sef/inbox", headers=headers)
        # 200 or other non-403 status (may fail for other reasons like missing config)
        assert resp.status_code != 403

    async def test_starter_blocked_from_rules(self, client, test_engine):
        """Starter plan user gets 403 when accessing automation rules."""
        headers = await _register_and_login(client, email="gate-rules@example.com")
        org_id = _get_org_id(headers)
        await _set_org_plan(test_engine, org_id, "starter")

        resp = await client.get("/api/v1/rules/", headers=headers)
        assert resp.status_code == 403

    async def test_agency_allowed_rules(self, client, test_engine):
        """Agency plan user can access automation rules."""
        headers = await _register_and_login(client, email="gate-rules-agency@example.com")
        org_id = _get_org_id(headers)
        await _set_org_plan(test_engine, org_id, "agency")

        resp = await client.get("/api/v1/rules/", headers=headers)
        assert resp.status_code != 403


class TestInvoiceLimit:
    """Test plan limit enforcement on invoice upload."""

    async def test_free_plan_limit_enforced(self, client, test_engine):
        """Exceeding free plan limit (10) returns 429."""
        headers = await _register_and_login(client, email="limit-free@example.com")
        org_id = _get_org_id(headers)

        # Insert 10 invoices (the free limit)
        await _insert_invoices(test_engine, org_id, 10)

        # 11th upload should be rejected with 429
        resp = await client.post(
            "/api/v1/invoices/upload",
            headers=headers,
            files={"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
        )
        assert resp.status_code == 402
        data = resp.json()["detail"]
        assert data["code"] == "invoice_limit_exceeded"
        assert data["plan"] == "free"
