"""Tests for portfolio view endpoint (M19.7)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token


async def _register_and_login(
    client: AsyncClient,
    email: str = "portfolio-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Portfolio",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Portfolio Test Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _set_org_plan(test_engine, org_id: str, plan: str) -> None:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("UPDATE organizations SET plan = :plan WHERE id = :org_id"),
            {"plan": plan, "org_id": org_id},
        )
        await session.commit()


async def test_portfolio_requires_agency_plan(client: AsyncClient, test_engine):
    """Non-agency plans cannot access the portfolio endpoint."""
    headers = await _register_and_login(client, "free-portfolio@example.com")
    resp = await client.get("/api/v1/portfolio", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "feature_unavailable"


async def test_portfolio_empty_on_agency_plan(client: AsyncClient, test_engine):
    """Agency plan with no clients returns an empty list."""
    headers = await _register_and_login(client, "agency-portfolio@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    resp = await client.get("/api/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    # Period is present and well-formed (YYYY-MM)
    assert len(body["period"]) == 7
    assert body["period"][4] == "-"


async def test_portfolio_returns_rows_for_created_clients(client: AsyncClient, test_engine):
    """Created clients appear in portfolio with zeroed indicators."""
    headers = await _register_and_login(client, "rows-portfolio@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    create_resp = await client.post(
        "/api/v1/clients/",
        headers=headers,
        json={"name": "Kafić Centar", "pib": "123456789"},
    )
    assert create_resp.status_code == 201

    resp = await client.get("/api/v1/portfolio", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Kafić Centar"
    assert row["pib"] == "123456789"
    assert row["invoice_count"] == 0
    assert row["pending_review_count"] == 0
    assert row["blocked_count"] == 0


async def test_portfolio_invalid_period_rejected(client: AsyncClient, test_engine):
    """Malformed period strings return 400."""
    headers = await _register_and_login(client, "badperiod-portfolio@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    resp = await client.get("/api/v1/portfolio?period=2025-13", headers=headers)
    assert resp.status_code == 400

    resp = await client.get("/api/v1/portfolio?period=not-a-period", headers=headers)
    assert resp.status_code == 400


async def test_portfolio_org_isolation(client: AsyncClient, test_engine):
    """Portfolio only returns clients for the authenticated user's organization."""
    headers_a = await _register_and_login(client, "iso-a-portfolio@example.com")
    org_a = _get_org_id(headers_a)
    await _set_org_plan(test_engine, org_a, "agency")
    await client.post(
        "/api/v1/clients/",
        headers=headers_a,
        json={"name": "Org A Client", "pib": "111111111"},
    )

    headers_b = await _register_and_login(client, "iso-b-portfolio@example.com")
    org_b = _get_org_id(headers_b)
    await _set_org_plan(test_engine, org_b, "agency")
    await client.post(
        "/api/v1/clients/",
        headers=headers_b,
        json={"name": "Org B Client", "pib": "222222222"},
    )

    resp_a = await client.get("/api/v1/portfolio", headers=headers_a)
    names_a = {r["name"] for r in resp_a.json()["data"]}
    assert names_a == {"Org A Client"}

    resp_b = await client.get("/api/v1/portfolio", headers=headers_b)
    names_b = {r["name"] for r in resp_b.json()["data"]}
    assert names_b == {"Org B Client"}
