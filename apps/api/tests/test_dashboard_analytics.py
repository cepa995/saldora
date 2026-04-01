"""Tests for dashboard analytics endpoint."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(
    client: AsyncClient,
    email: str,
    org_name: str = "Dashboard Org",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice_id = uuid4()
        invoice = Invoice(
            id=invoice_id,
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", f"INV-{uuid4().hex[:6]}"),
            invoice_date=overrides.get("invoice_date", date(2026, 3, 15)),
            seller=overrides.get("seller", {"name": "Test Seller", "pib": "123456789"}),
            total_amount=overrides.get("total_amount", Decimal("1000.00")),
            client_id=overrides.get("client_id"),
        )
        session.add(invoice)
        await session.commit()
        return str(invoice_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_dashboard_stats_returns_all_sections(client: AsyncClient):
    """Dashboard endpoint returns all 3 chart sections."""
    headers = await _register_and_login(client, "dash-all@test.com")
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_volume" in data
    assert "status_distribution" in data
    assert "monthly_totals" in data
    assert isinstance(data["monthly_volume"], list)
    assert isinstance(data["status_distribution"], list)
    assert isinstance(data["monthly_totals"], list)
    # Always returns 12 months of data
    assert len(data["monthly_volume"]) == 12
    assert len(data["monthly_totals"]) == 12


async def test_dashboard_stats_empty_org(client: AsyncClient):
    """New org with no invoices returns zeros."""
    headers = await _register_and_login(client, "dash-empty@test.com")
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status_distribution"] == []
    assert all(m["count"] == 0 for m in data["monthly_volume"])
    assert all(m["total_rsd"] == 0.0 for m in data["monthly_totals"])


async def test_dashboard_stats_monthly_volume(client: AsyncClient, test_engine):
    """Monthly volume correctly groups invoices by month."""
    headers = await _register_and_login(client, "dash-volume@test.com")
    org_id = _get_org_id(headers)

    # Insert 3 invoices in current month
    for _ in range(3):
        await _insert_invoice(test_engine, org_id)

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Current month should have count=3
    current_month = datetime.now().strftime("%Y-%m")
    month_data = [m for m in data["monthly_volume"] if m["month"] == current_month]
    assert len(month_data) == 1
    assert month_data[0]["count"] == 3


async def test_dashboard_stats_status_distribution(client: AsyncClient, test_engine):
    """Status distribution correctly counts invoices by status."""
    headers = await _register_and_login(client, "dash-status@test.com")
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id, status="review")
    await _insert_invoice(test_engine, org_id, status="review")
    await _insert_invoice(test_engine, org_id, status="verified")

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    status_map = {s["status"]: s["count"] for s in data["status_distribution"]}
    assert status_map.get("review") == 2
    assert status_map.get("verified") == 1


async def test_dashboard_stats_monthly_totals(client: AsyncClient, test_engine):
    """Monthly totals correctly sums invoice amounts."""
    headers = await _register_and_login(client, "dash-totals@test.com")
    org_id = _get_org_id(headers)

    await _insert_invoice(test_engine, org_id, total_amount=Decimal("5000.00"))
    await _insert_invoice(test_engine, org_id, total_amount=Decimal("3000.50"))

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    current_month = datetime.now().strftime("%Y-%m")
    month_data = [m for m in data["monthly_totals"] if m["month"] == current_month]
    assert len(month_data) == 1
    assert month_data[0]["total_rsd"] == 8000.50


async def test_dashboard_stats_org_isolation(client: AsyncClient, test_engine):
    """Org A's invoices are not visible to org B."""
    headers_a = await _register_and_login(client, "dash-iso-a@test.com", org_name="Org A")
    headers_b = await _register_and_login(client, "dash-iso-b@test.com", org_name="Org B")
    org_a = _get_org_id(headers_a)

    # Insert invoices only in org A
    for _ in range(3):
        await _insert_invoice(test_engine, org_a)

    # Org B should see nothing
    resp_b = await client.get("/api/v1/analytics/dashboard", headers=headers_b)
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["status_distribution"] == []
    assert all(m["count"] == 0 for m in data_b["monthly_volume"])

    # Org A should see its invoices
    resp_a = await client.get("/api/v1/analytics/dashboard", headers=headers_a)
    data_a = resp_a.json()
    total_volume = sum(m["count"] for m in data_a["monthly_volume"])
    assert total_volume == 3


async def test_dashboard_stats_requires_auth(client: AsyncClient):
    """Dashboard endpoint requires authentication."""
    resp = await client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 401
