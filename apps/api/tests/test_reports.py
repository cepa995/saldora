"""Tests for Saldora reports API endpoints.

Covers all five report templates: received goods, spending by supplier,
monthly breakdown, price comparison, and expense summary.
"""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _auth_headers(
    client: AsyncClient,
    test_engine,
    email: str,
    org_name: str,
    plan: str = "pro",
) -> dict[str, str]:
    """Register a user, create an organization, upgrade plan, and return Authorization headers.

    Args:
        client: Test HTTP client.
        test_engine: SQLAlchemy async engine for the test database.
        email: Email address to register.
        org_name: Organization name to create.
        plan: Plan tier to assign (default: pro).

    Returns:
        Authorization headers dict with Bearer token.
    """
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Report",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]

    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]

    if plan != "free":
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            await session.execute(
                text("UPDATE organizations SET plan = :plan WHERE name = :name"),
                {"plan": plan, "name": org_name},
            )
            await session.commit()

    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers.

    Args:
        headers: Authorization headers dict containing a Bearer token.

    Returns:
        Organization UUID as a string.
    """
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _insert_invoice(test_engine, org_id: str) -> str:
    """Insert a minimal invoice row and return its UUID string.

    Args:
        test_engine: SQLAlchemy async engine for the test database.
        org_id: Organization UUID as a string.

    Returns:
        Invoice UUID as a string.
    """
    inv_id = str(uuid4())
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO invoices"
                " (id, organization_id, status, currency, created_at, updated_at)"
                " VALUES (:id, :org_id, 'verified', 'RSD', NOW(), NOW())"
            ),
            {"id": inv_id, "org_id": org_id},
        )
        await session.commit()
    return inv_id


async def _insert_line_item(test_engine, **fields) -> str:
    """Insert a row directly into invoice_line_items and return its UUID string.

    Args:
        test_engine: SQLAlchemy async engine for the test database.
        **fields: Column values. Required: invoice_id, organization_id, total.
            Optional: description, quantity, unit_price, tax_rate, tax_amount,
            seller_name, seller_pib, invoice_date, currency.

    Returns:
        Line item UUID as a string.
    """
    item_id = str(uuid4())
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO invoice_line_items "
                "(id, invoice_id, organization_id, description, quantity, unit_price, "
                "total, tax_rate, tax_amount, seller_name, seller_pib, invoice_date, "
                "currency, created_at) "
                "VALUES (:id, :invoice_id, :organization_id, :description, :quantity, "
                ":unit_price, :total, :tax_rate, :tax_amount, :seller_name, :seller_pib, "
                ":invoice_date, :currency, NOW())"
            ),
            {
                "id": item_id,
                "invoice_id": fields["invoice_id"],
                "organization_id": fields["organization_id"],
                "description": fields.get("description", "Test stavka"),
                "quantity": fields.get("quantity", 1),
                "unit_price": fields.get("unit_price", 100),
                "total": fields["total"],
                "tax_rate": fields.get("tax_rate", None),
                "tax_amount": fields.get("tax_amount", None),
                "seller_name": fields.get("seller_name", None),
                "seller_pib": fields.get("seller_pib", None),
                "invoice_date": fields.get("invoice_date", None),
                "currency": fields.get("currency", "RSD"),
            },
        )
        await session.commit()
    return item_id


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def test_reports_require_auth(client: AsyncClient) -> None:
    """All report endpoints return 401 when no Authorization header is provided."""
    endpoints = [
        "/api/v1/reports/received-goods",
        "/api/v1/reports/spending-by-supplier",
        "/api/v1/reports/monthly-breakdown",
        "/api/v1/reports/price-comparison?search=test",
        "/api/v1/reports/expense-summary",
    ]
    for url in endpoints:
        resp = await client.get(url)
        assert resp.status_code == 401, f"Expected 401 for {url}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Received Goods
# ---------------------------------------------------------------------------


async def test_received_goods_empty(client: AsyncClient, test_engine) -> None:
    """Received-goods returns an empty items list when no line items exist."""
    headers = await _auth_headers(client, test_engine, "rpt-rg-empty@example.com", "RPT RG Empty")

    resp = await client.get("/api/v1/reports/received-goods", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["grand_total"] == 0.0
    assert body["item_count"] == 0


async def test_received_goods_groups_by_description(client: AsyncClient, test_engine) -> None:
    """Received-goods groups line items with the same description into one row."""
    headers = await _auth_headers(client, test_engine, "rpt-rg-group@example.com", "RPT RG Group")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Kancelarijski materijal",
        quantity=2,
        unit_price=500,
        total=1000,
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Kancelarijski materijal",
        quantity=3,
        unit_price=500,
        total=1500,
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Toneri",
        quantity=1,
        unit_price=3000,
        total=3000,
    )

    resp = await client.get("/api/v1/reports/received-goods", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_count"] == 2

    descs = [item["description"] for item in body["items"]]
    assert "Kancelarijski materijal" in descs
    assert "Toneri" in descs


async def test_received_goods_sums_correctly(client: AsyncClient, test_engine) -> None:
    """Received-goods correctly aggregates total_quantity, total_amount, and avg_unit_price."""
    headers = await _auth_headers(client, test_engine, "rpt-rg-sums@example.com", "RPT RG Sums")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Papir A4",
        quantity=10,
        unit_price=200,
        total=2000,
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Papir A4",
        quantity=5,
        unit_price=400,
        total=2000,
    )

    resp = await client.get("/api/v1/reports/received-goods", headers=headers)

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1

    item = items[0]
    assert item["description"] == "Papir A4"
    assert item["total_quantity"] == pytest.approx(15.0)
    assert item["total_amount"] == pytest.approx(4000.0)
    # avg of 200 and 400
    assert item["avg_unit_price"] == pytest.approx(300.0)


async def test_received_goods_date_filter(client: AsyncClient, test_engine) -> None:
    """Received-goods excludes line items outside the requested date range."""
    headers = await _auth_headers(client, test_engine, "rpt-rg-date@example.com", "RPT RG Date")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    # Inside range
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="U opsegu",
        quantity=1,
        unit_price=100,
        total=100,
        invoice_date=date(2025, 6, 15),
    )
    # Outside range
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Van opsega",
        quantity=1,
        unit_price=200,
        total=200,
        invoice_date=date(2024, 1, 1),
    )

    resp = await client.get(
        "/api/v1/reports/received-goods",
        params={"date_from": "2025-01-01", "date_to": "2025-12-31"},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_count"] == 1
    assert body["items"][0]["description"] == "U opsegu"


async def test_received_goods_search_filter(client: AsyncClient, test_engine) -> None:
    """Received-goods filters by description using case-insensitive substring match."""
    headers = await _auth_headers(client, test_engine, "rpt-rg-search@example.com", "RPT RG Search")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Kancelarijski pribor",
        total=500,
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="IT oprema",
        total=1000,
    )

    resp = await client.get(
        "/api/v1/reports/received-goods",
        params={"search": "kancelarij"},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_count"] == 1
    assert body["items"][0]["description"] == "Kancelarijski pribor"


async def test_received_goods_org_isolation(client: AsyncClient, test_engine) -> None:
    """Received-goods does not expose line items belonging to another organization."""
    headers_a = await _auth_headers(client, test_engine, "rpt-rg-iso-a@example.com", "RPT RG Iso A")
    headers_b = await _auth_headers(client, test_engine, "rpt-rg-iso-b@example.com", "RPT RG Iso B")
    org_id_b = _get_org_id(headers_b)
    inv_id_b = await _insert_invoice(test_engine, org_id_b)

    # Insert item belonging to org B
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id_b,
        organization_id=org_id_b,
        description="Stavka org B",
        total=9999,
    )

    # Org A should see nothing
    resp = await client.get("/api/v1/reports/received-goods", headers=headers_a)

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_count"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Spending by Supplier
# ---------------------------------------------------------------------------


async def test_spending_by_supplier_groups(client: AsyncClient, test_engine) -> None:
    """Spending-by-supplier groups line items per seller and computes correct totals."""
    headers = await _auth_headers(client, test_engine, "rpt-sbs-group@example.com", "RPT SBS Group")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Papir",
        total=1000,
        seller_name="Dobavljac A",
        seller_pib="111111111",
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Toneri",
        total=2000,
        seller_name="Dobavljac A",
        seller_pib="111111111",
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Laptop",
        total=80000,
        seller_name="Dobavljac B",
        seller_pib="222222222",
    )

    resp = await client.get("/api/v1/reports/spending-by-supplier", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2

    by_pib = {item["seller_pib"]: item for item in body["items"]}
    assert by_pib["111111111"]["total_amount"] == pytest.approx(3000.0)
    assert by_pib["222222222"]["total_amount"] == pytest.approx(80000.0)
    assert body["grand_total"] == pytest.approx(83000.0)


async def test_spending_by_supplier_invoice_count(client: AsyncClient, test_engine) -> None:
    """Spending-by-supplier counts distinct invoice_ids per supplier correctly."""
    headers = await _auth_headers(client, test_engine, "rpt-sbs-count@example.com", "RPT SBS Count")
    org_id = _get_org_id(headers)

    inv_id1 = await _insert_invoice(test_engine, org_id)
    inv_id2 = await _insert_invoice(test_engine, org_id)

    for inv_id in (inv_id1, inv_id2):
        await _insert_line_item(
            test_engine,
            invoice_id=inv_id,
            organization_id=org_id,
            description="Usluga",
            total=5000,
            seller_name="Servis DOO",
            seller_pib="333333333",
        )

    resp = await client.get("/api/v1/reports/spending-by-supplier", headers=headers)

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["invoice_count"] == 2


# ---------------------------------------------------------------------------
# Monthly Breakdown
# ---------------------------------------------------------------------------


async def test_monthly_breakdown_returns_items(client: AsyncClient, test_engine) -> None:
    """Monthly-breakdown returns individual line items with correct fields."""
    headers = await _auth_headers(client, test_engine, "rpt-mb-items@example.com", "RPT MB Items")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    await _insert_line_item(
        test_engine,
        invoice_id=inv_id,
        organization_id=org_id,
        description="Konsultacije",
        quantity=2,
        unit_price=5000,
        total=10000,
        seller_name="Konsultant DOO",
        invoice_date=date(2025, 3, 10),
    )

    resp = await client.get("/api/v1/reports/monthly-breakdown", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_count"] == 1
    assert body["total_amount"] == pytest.approx(10000.0)

    item = body["items"][0]
    assert item["description"] == "Konsultacije"
    assert item["total"] == pytest.approx(10000.0)
    assert item["invoice_id"] == inv_id
    assert item["invoice_date"] == "2025-03-10"


async def test_monthly_breakdown_pagination(client: AsyncClient, test_engine) -> None:
    """Monthly-breakdown correctly paginates: page 1 and page 2 return distinct rows."""
    headers = await _auth_headers(client, test_engine, "rpt-mb-page@example.com", "RPT MB Page")
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    for i in range(5):
        await _insert_line_item(
            test_engine,
            invoice_id=inv_id,
            organization_id=org_id,
            description=f"Stavka {i}",
            total=100 * (i + 1),
            invoice_date=date(2025, 1, i + 1),
        )

    resp_p1 = await client.get(
        "/api/v1/reports/monthly-breakdown",
        params={"page": 1, "per_page": 3},
        headers=headers,
    )
    resp_p2 = await client.get(
        "/api/v1/reports/monthly-breakdown",
        params={"page": 2, "per_page": 3},
        headers=headers,
    )

    assert resp_p1.status_code == 200
    assert resp_p2.status_code == 200

    body_p1 = resp_p1.json()
    body_p2 = resp_p2.json()

    assert body_p1["item_count"] == 5
    assert len(body_p1["items"]) == 3
    assert len(body_p2["items"]) == 2

    ids_p1 = {item["id"] for item in body_p1["items"]}
    ids_p2 = {item["id"] for item in body_p2["items"]}
    assert ids_p1.isdisjoint(ids_p2), "Pages must not share the same line item IDs"


# ---------------------------------------------------------------------------
# Price Comparison
# ---------------------------------------------------------------------------


async def test_price_comparison_requires_search(client: AsyncClient, test_engine) -> None:
    """Price-comparison returns 200 when no search parameter is provided (search is optional)."""
    headers = await _auth_headers(
        client, test_engine, "rpt-pc-nosearch@example.com", "RPT PC NoSearch"
    )

    resp = await client.get("/api/v1/reports/price-comparison", headers=headers)

    assert resp.status_code == 200


async def test_price_comparison_shows_suppliers(client: AsyncClient, test_engine) -> None:
    """Price-comparison returns one row per (description, supplier) with correct price stats."""
    headers = await _auth_headers(
        client, test_engine, "rpt-pc-suppliers@example.com", "RPT PC Suppliers"
    )
    org_id = _get_org_id(headers)

    inv_a = await _insert_invoice(test_engine, org_id)
    inv_b = await _insert_invoice(test_engine, org_id)

    await _insert_line_item(
        test_engine,
        invoice_id=inv_a,
        organization_id=org_id,
        description="Papir A4 500 listova",
        quantity=10,
        unit_price=200,
        total=2000,
        seller_name="Dobavljac A",
        seller_pib="444444444",
    )
    await _insert_line_item(
        test_engine,
        invoice_id=inv_b,
        organization_id=org_id,
        description="Papir A4 500 listova",
        quantity=10,
        unit_price=180,
        total=1800,
        seller_name="Dobavljac B",
        seller_pib="555555555",
    )

    resp = await client.get(
        "/api/v1/reports/price-comparison",
        params={"search": "Papir A4"},
        headers=headers,
    )

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2

    by_pib = {item["seller_pib"]: item for item in items}
    assert by_pib["444444444"]["avg_unit_price"] == pytest.approx(200.0)
    assert by_pib["444444444"]["min_unit_price"] == pytest.approx(200.0)
    assert by_pib["444444444"]["max_unit_price"] == pytest.approx(200.0)
    assert by_pib["555555555"]["avg_unit_price"] == pytest.approx(180.0)


# ---------------------------------------------------------------------------
# Expense Summary
# ---------------------------------------------------------------------------


async def test_expense_summary_monthly_buckets(client: AsyncClient, test_engine) -> None:
    """Expense-summary groups line items into correct monthly buckets."""
    headers = await _auth_headers(
        client, test_engine, "rpt-es-monthly@example.com", "RPT ES Monthly"
    )
    org_id = _get_org_id(headers)
    inv_id = await _insert_invoice(test_engine, org_id)

    items_by_month = [
        (date(2025, 1, 10), 1000),
        (date(2025, 1, 20), 2000),
        (date(2025, 2, 5), 3000),
        (date(2025, 3, 15), 4000),
    ]
    for inv_date, total in items_by_month:
        await _insert_line_item(
            test_engine,
            invoice_id=inv_id,
            organization_id=org_id,
            description="Usluga",
            total=total,
            invoice_date=inv_date,
        )

    resp = await client.get(
        "/api/v1/reports/expense-summary",
        params={"group_by": "month"},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    buckets = body["buckets"]
    assert len(buckets) == 3

    by_period = {b["period"]: b for b in buckets}
    assert "2025-01" in by_period
    assert "2025-02" in by_period
    assert "2025-03" in by_period

    assert by_period["2025-01"]["total_amount"] == pytest.approx(3000.0)
    assert by_period["2025-01"]["item_count"] == 2
    assert by_period["2025-02"]["total_amount"] == pytest.approx(3000.0)
    assert by_period["2025-03"]["total_amount"] == pytest.approx(4000.0)
    assert body["grand_total"] == pytest.approx(10000.0)
