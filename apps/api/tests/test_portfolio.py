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
    # total_amount is present and coalesces to "0" for a client with no invoices.
    # The /klijenti grid renders this on the card metric band.
    assert row["total_amount"] == "0"


async def test_portfolio_sums_total_amount_across_client_invoices(client: AsyncClient, test_engine):
    """total_amount on a portfolio row equals the sum of the client's invoice totals."""
    from datetime import date
    from decimal import Decimal
    from uuid import UUID, uuid4

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.invoice import Invoice

    headers = await _register_and_login(client, "total-amount-portfolio@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    create_resp = await client.post(
        "/api/v1/clients/",
        headers=headers,
        json={"name": "Aroma", "pib": "987654321"},
    )
    assert create_resp.status_code == 201
    client_id = create_resp.json()["id"]

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for amount in (Decimal("1200.50"), Decimal("800.25"), Decimal("50.00")):
            session.add(
                Invoice(
                    id=uuid4(),
                    organization_id=UUID(org_id),
                    client_id=UUID(client_id),
                    status="verified",
                    invoice_number=f"INV-{amount}",
                    invoice_date=date(2026, 4, 1),
                    seller={"name": "S", "pib": "100000001"},
                    buyer={"name": "B", "pib": "100000002"},
                    subtotal=amount,
                    tax_rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    total_amount=amount,
                    currency="RSD",
                )
            )
        await session.commit()

    # Pin the period so the test is date-independent (invoices above are April 2026).
    resp = await client.get("/api/v1/portfolio?period=2026-04", headers=headers)
    row = next(r for r in resp.json()["data"] if r["client_id"] == client_id)
    assert row["invoice_count"] == 3
    assert Decimal(row["total_amount"]) == Decimal("2050.75")


async def test_portfolio_scopes_counts_by_invoice_date(client: AsyncClient, test_engine):
    """Period filters invoice_count / total_amount by invoice_date.

    Invoices dated outside the requested month must NOT be included in the
    period-scoped counts, even if they belong to the client.
    """
    from datetime import date
    from decimal import Decimal
    from uuid import UUID, uuid4

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.invoice import Invoice

    headers = await _register_and_login(client, "scope-period@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    create_resp = await client.post(
        "/api/v1/clients/",
        headers=headers,
        json={"name": "Scope Client", "pib": "555555555"},
    )
    client_id = create_resp.json()["id"]

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for d, amount in [
            (date(2026, 3, 15), Decimal("100")),  # March — excluded when period=April
            (date(2026, 4, 2), Decimal("200")),
            (date(2026, 4, 20), Decimal("300")),
            (date(2026, 5, 1), Decimal("900")),  # May — excluded when period=April
        ]:
            session.add(
                Invoice(
                    id=uuid4(),
                    organization_id=UUID(org_id),
                    client_id=UUID(client_id),
                    status="verified",
                    invoice_number=f"INV-{d}",
                    invoice_date=d,
                    seller={"name": "S", "pib": "100000001"},
                    buyer={"name": "B", "pib": "100000002"},
                    subtotal=amount,
                    tax_rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    total_amount=amount,
                    currency="RSD",
                )
            )
        await session.commit()

    resp = await client.get("/api/v1/portfolio?period=2026-04", headers=headers)
    assert resp.status_code == 200
    row = next(r for r in resp.json()["data"] if r["client_id"] == client_id)
    assert row["invoice_count"] == 2
    assert Decimal(row["total_amount"]) == Decimal("500")


async def test_portfolio_monthly_series_is_six_zero_padded_points(client: AsyncClient, test_engine):
    """monthly_series has exactly 6 points ending at the requested period.

    Months with no invoices are zero-filled so every client's sparkline has
    the same axis.
    """
    from datetime import date
    from decimal import Decimal
    from uuid import UUID, uuid4

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.invoice import Invoice

    headers = await _register_and_login(client, "monthly-series@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    create_resp = await client.post(
        "/api/v1/clients/",
        headers=headers,
        json={"name": "Series Client", "pib": "666666666"},
    )
    client_id = create_resp.json()["id"]

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for d, amount in [
            (date(2026, 2, 10), Decimal("100")),
            (date(2026, 2, 20), Decimal("150")),
            (date(2026, 4, 5), Decimal("300")),
        ]:
            session.add(
                Invoice(
                    id=uuid4(),
                    organization_id=UUID(org_id),
                    client_id=UUID(client_id),
                    status="verified",
                    invoice_number=f"INV-{d}",
                    invoice_date=d,
                    seller={"name": "S", "pib": "100000001"},
                    buyer={"name": "B", "pib": "100000002"},
                    subtotal=amount,
                    tax_rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    total_amount=amount,
                    currency="RSD",
                )
            )
        await session.commit()

    resp = await client.get("/api/v1/portfolio?period=2026-04", headers=headers)
    row = next(r for r in resp.json()["data"] if r["client_id"] == client_id)
    series = row["monthly_series"]

    # Trailing 6 months ending April 2026
    assert [p["period"] for p in series] == [
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
    ]
    by_period = {p["period"]: p for p in series}
    assert by_period["2025-11"]["invoice_count"] == 0
    assert Decimal(by_period["2025-11"]["total_amount"]) == Decimal("0")
    assert by_period["2026-02"]["invoice_count"] == 2
    assert Decimal(by_period["2026-02"]["total_amount"]) == Decimal("250")
    assert by_period["2026-04"]["invoice_count"] == 1
    assert Decimal(by_period["2026-04"]["total_amount"]) == Decimal("300")


async def test_portfolio_past_due_count_is_period_agnostic(client: AsyncClient, test_engine):
    """past_due_count counts overdue invoices regardless of requested period.

    "Overdue right now" is what the card surfaces — scoping it to the viewed
    month would hide an old-and-still-late invoice when browsing a newer
    month. The count drops only when the invoice is exported (settled).
    """
    from datetime import date, timedelta
    from decimal import Decimal
    from uuid import UUID, uuid4

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.invoice import Invoice

    headers = await _register_and_login(client, "past-due-portfolio@example.com")
    org_id = _get_org_id(headers)
    await _set_org_plan(test_engine, org_id, "agency")

    create_resp = await client.post(
        "/api/v1/clients/",
        headers=headers,
        json={"name": "Past Due Client", "pib": "909090909"},
    )
    client_id = create_resp.json()["id"]

    today = date.today()
    past = today - timedelta(days=15)
    future = today + timedelta(days=20)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Two past-due invoices — one review, one verified (both still late)
        for status in ("review", "verified"):
            session.add(
                Invoice(
                    id=uuid4(),
                    organization_id=UUID(org_id),
                    client_id=UUID(client_id),
                    status=status,
                    invoice_number=f"LATE-{status}",
                    invoice_date=past,
                    due_date=past,
                    seller={"name": "S", "pib": "100000001"},
                    buyer={"name": "B", "pib": "100000002"},
                    subtotal=Decimal("100"),
                    tax_rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    total_amount=Decimal("100"),
                    currency="RSD",
                )
            )
        # One exported-late invoice — NOT counted, it's settled
        session.add(
            Invoice(
                id=uuid4(),
                organization_id=UUID(org_id),
                client_id=UUID(client_id),
                status="exported",
                invoice_number="LATE-exported",
                invoice_date=past,
                due_date=past,
                seller={"name": "S", "pib": "100000001"},
                buyer={"name": "B", "pib": "100000002"},
                subtotal=Decimal("50"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total_amount=Decimal("50"),
                currency="RSD",
            )
        )
        # One future-dated invoice — NOT counted
        session.add(
            Invoice(
                id=uuid4(),
                organization_id=UUID(org_id),
                client_id=UUID(client_id),
                status="review",
                invoice_number="FUTURE",
                invoice_date=future,
                due_date=future,
                seller={"name": "S", "pib": "100000001"},
                buyer={"name": "B", "pib": "100000002"},
                subtotal=Decimal("200"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total_amount=Decimal("200"),
                currency="RSD",
            )
        )
        await session.commit()

    # Query a period where none of the invoices fall — past_due_count should
    # still be 2 because it's agnostic of the requested window.
    resp = await client.get("/api/v1/portfolio?period=2030-06", headers=headers)
    row = next(r for r in resp.json()["data"] if r["client_id"] == client_id)
    assert row["past_due_count"] == 2


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
