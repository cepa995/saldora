"""
Tests for the analytics router (GET /dashboard, GET /corrections).

Invoices and correction logs are inserted directly into the test DB to
avoid coupling analytics tests to the upload/OCR flow.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.client import Client
from app.models.correction_log import CorrectionLog
from app.models.invoice import Invoice


async def _auth_headers(
    client: AsyncClient,
    test_engine,
    email: str = "ana-default@example.com",
    org_name: str = "AnaOrg",
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


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers.

    Args:
        headers: Authorization headers dict.

    Returns:
        Organization UUID string.
    """
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


def _get_user_id(headers: dict) -> str:
    """Extract user_id from the JWT token in auth headers.

    Args:
        headers: Authorization headers dict.

    Returns:
        User UUID string.
    """
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["sub"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id.

    Args:
        test_engine: SQLAlchemy async engine (from conftest fixture).
        org_id: Organization UUID string.
        **overrides: Any Invoice column overrides.

    Returns:
        String UUID of the created invoice.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice = Invoice(
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2025, 1, 15)),
            due_date=overrides.get("due_date", date(2025, 2, 15)),
            seller=overrides.get(
                "seller",
                {"pib": "123456789", "name": "Prodavac DOO", "address": "Beograd"},
            ),
            buyer=overrides.get(
                "buyer",
                {"pib": "987654321", "name": "Kupac DOO", "address": "Novi Sad"},
            ),
            subtotal=overrides.get("subtotal", Decimal("10000.00")),
            tax_rate=overrides.get("tax_rate", Decimal("20.00")),
            tax_amount=overrides.get("tax_amount", Decimal("2000.00")),
            total_amount=overrides.get("total_amount", Decimal("12000.00")),
            currency=overrides.get("currency", "RSD"),
            line_items=overrides.get(
                "line_items",
                [
                    {
                        "description": "Usluga 1",
                        "quantity": "1.00",
                        "unit_price": "10000.00",
                        "total": "10000.00",
                    }
                ],
            ),
            tax_groups=overrides.get("tax_groups", None),
            document_hash=overrides.get("document_hash", uuid4().hex),
            document_path=overrides.get("document_path", "orgs/test/inv/original.pdf"),
            document_content_type=overrides.get("document_content_type", "application/pdf"),
            confidence_score=overrides.get("confidence_score", Decimal("0.85")),
            field_confidence=overrides.get(
                "field_confidence",
                [
                    {
                        "field_name": "invoice_number",
                        "value": "INV-001",
                        "confidence": 0.95,
                        "needs_review": False,
                    }
                ],
            ),
            warnings=overrides.get("warnings", []),
            ocr_engine=overrides.get("ocr_engine", "dots"),
            processing_time_ms=overrides.get("processing_time_ms", 3500),
            raw_ocr_text=overrides.get("raw_ocr_text", "Sample OCR text"),
            client_id=overrides.get("client_id", None),
            created_at=overrides.get("created_at", None),
        )
        session.add(invoice)
        await session.commit()
        await session.refresh(invoice)
        return str(invoice.id)


async def _insert_correction(
    test_engine,
    invoice_id: str,
    org_id: str,
    user_id: str,
    field_name: str = "invoice_number",
    original_value: str | None = "ORIG-001",
    corrected_value: str = "CORR-001",
    model_confidence: float | None = 0.75,
) -> None:
    """Insert a correction log entry directly into the DB.

    Args:
        test_engine: SQLAlchemy async engine (from conftest fixture).
        invoice_id: Invoice UUID string.
        org_id: Organization UUID string.
        user_id: User UUID string.
        field_name: Name of the corrected field.
        original_value: Original OCR-extracted value.
        corrected_value: User-supplied corrected value.
        model_confidence: Model confidence score at extraction time.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        log = CorrectionLog(
            invoice_id=invoice_id,
            organization_id=org_id,
            user_id=user_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            model_confidence=model_confidence,
        )
        session.add(log)
        await session.commit()


# ── GET /analytics/dashboard ───────────────────────────────────────────────────


async def test_dashboard_requires_auth(client: AsyncClient):
    """GET /dashboard without token returns 401."""
    resp = await client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 401


async def test_dashboard_empty_org(client: AsyncClient, test_engine):
    """GET /dashboard for an org with no invoices returns zeros."""
    headers = await _auth_headers(
        client, test_engine, email="ana-empty@example.com", org_name="AnaEmptyOrg"
    )
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_volume" in data
    assert "status_distribution" in data
    assert "monthly_totals" in data
    # No invoices — all months should be zero
    assert all(m["count"] == 0 for m in data["monthly_volume"])
    assert all(m["total_rsd"] == 0.0 for m in data["monthly_totals"])
    assert data["status_distribution"] == []


async def test_dashboard_returns_12_months(client: AsyncClient, test_engine):
    """GET /dashboard always returns exactly 12 monthly buckets."""
    headers = await _auth_headers(
        client, test_engine, email="ana-12m@example.com", org_name="Ana12mOrg"
    )
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["monthly_volume"]) == 12
    assert len(data["monthly_totals"]) == 12


async def test_dashboard_with_invoices(client: AsyncClient, test_engine):
    """GET /dashboard counts invoices created in the current month."""
    headers = await _auth_headers(
        client, test_engine, email="ana-with@example.com", org_name="AnaWithOrg"
    )
    org_id = _get_org_id(headers)
    # Insert 3 invoices (created_at defaults to now)
    for i in range(3):
        await _insert_invoice(test_engine, org_id, invoice_number=f"ANA-{i:03d}")

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Total count across all months should equal 3
    total_count = sum(m["count"] for m in data["monthly_volume"])
    assert total_count == 3


async def test_dashboard_status_distribution(client: AsyncClient, test_engine):
    """GET /dashboard status_distribution reflects actual invoice statuses."""
    headers = await _auth_headers(
        client, test_engine, email="ana-status@example.com", org_name="AnaStatusOrg"
    )
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id, status="review", invoice_number="S-001")
    await _insert_invoice(test_engine, org_id, status="review", invoice_number="S-002")
    await _insert_invoice(test_engine, org_id, status="verified", invoice_number="S-003")

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    distribution = {row["status"]: row["count"] for row in resp.json()["status_distribution"]}
    assert distribution.get("review") == 2
    assert distribution.get("verified") == 1


async def test_dashboard_monthly_totals_sum(client: AsyncClient, test_engine):
    """GET /dashboard monthly_totals sum reflects total_amount values."""
    headers = await _auth_headers(
        client, test_engine, email="ana-totals@example.com", org_name="AnaTotalsOrg"
    )
    org_id = _get_org_id(headers)
    await _insert_invoice(
        test_engine, org_id, total_amount=Decimal("5000.00"), invoice_number="T-001"
    )
    await _insert_invoice(
        test_engine, org_id, total_amount=Decimal("3000.00"), invoice_number="T-002"
    )

    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    total_rsd = sum(m["total_rsd"] for m in resp.json()["monthly_totals"])
    assert total_rsd == 8000.0


async def test_dashboard_org_isolation(client: AsyncClient, test_engine):
    """GET /dashboard does not include invoices from other organizations."""
    headers_a = await _auth_headers(
        client, test_engine, email="ana-isola@example.com", org_name="AnaIsolA"
    )
    headers_b = await _auth_headers(
        client, test_engine, email="ana-isolb@example.com", org_name="AnaIsolB"
    )
    org_id_b = _get_org_id(headers_b)

    # Insert 5 invoices into org B
    for i in range(5):
        await _insert_invoice(test_engine, org_id_b, invoice_number=f"B-{i:03d}")

    # Org A should see zero
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers_a)
    assert resp.status_code == 200
    total = sum(m["count"] for m in resp.json()["monthly_volume"])
    assert total == 0


async def test_dashboard_month_keys_format(client: AsyncClient, test_engine):
    """GET /dashboard month keys follow YYYY-MM format."""
    import re

    headers = await _auth_headers(
        client, test_engine, email="ana-fmt@example.com", org_name="AnaFmtOrg"
    )
    resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    pattern = re.compile(r"^\d{4}-\d{2}$")
    for bucket in resp.json()["monthly_volume"]:
        assert pattern.match(bucket["month"]), f"Bad month format: {bucket['month']}"


async def test_dashboard_filtered_by_client_id(client: AsyncClient, test_engine):
    """GET /dashboard?client_id= returns only invoices for that client."""
    headers = await _auth_headers(
        client, test_engine, email="ana-clt@example.com", org_name="AnaCltOrg"
    )
    org_id = _get_org_id(headers)

    # Create two client records via ORM (pib is required and unique per org)
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        target_client = Client(
            organization_id=org_id,
            name="Target Client",
            pib="111000111",
        )
        other_client = Client(
            organization_id=org_id,
            name="Other Client",
            pib="222000222",
        )
        db.add(target_client)
        db.add(other_client)
        await db.commit()
        await db.refresh(target_client)
        await db.refresh(other_client)
        target_client_id = target_client.id
        other_client_id = other_client.id

    # Insert invoices belonging to different clients
    await _insert_invoice(test_engine, org_id, client_id=target_client_id, invoice_number="CLT-001")
    await _insert_invoice(test_engine, org_id, client_id=target_client_id, invoice_number="CLT-002")
    await _insert_invoice(test_engine, org_id, client_id=other_client_id, invoice_number="CLT-003")
    await _insert_invoice(test_engine, org_id, client_id=None, invoice_number="CLT-004")

    resp = await client.get(
        f"/api/v1/analytics/dashboard?client_id={target_client_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    total = sum(m["count"] for m in resp.json()["monthly_volume"])
    assert total == 2


async def test_dashboard_filtered_by_invalid_client_id(client: AsyncClient, test_engine):
    """GET /dashboard with non-existent client_id returns empty data."""
    headers = await _auth_headers(
        client, test_engine, email="ana-badclt@example.com", org_name="AnaBadCltOrg"
    )
    org_id = _get_org_id(headers)

    # Insert some invoices (without client)
    await _insert_invoice(test_engine, org_id, invoice_number="BCLT-001")

    nonexistent = uuid4()
    resp = await client.get(
        f"/api/v1/analytics/dashboard?client_id={nonexistent}",
        headers=headers,
    )
    assert resp.status_code == 200
    total = sum(m["count"] for m in resp.json()["monthly_volume"])
    assert total == 0


# ── GET /analytics/corrections ─────────────────────────────────────────────────


async def test_corrections_requires_auth(client: AsyncClient):
    """GET /corrections without token returns 401."""
    resp = await client.get("/api/v1/analytics/corrections")
    assert resp.status_code == 401


async def test_corrections_empty_returns_empty_lists(client: AsyncClient, test_engine):
    """GET /corrections returns empty lists when org has no corrections."""
    headers = await _auth_headers(
        client, test_engine, email="ana-cor0@example.com", org_name="AnaCorEmptyOrg"
    )
    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_error_rates"] == []
    assert data["high_confidence_errors"] == []
    assert data["repeat_patterns"] == []


async def test_corrections_basic_field_error_rates(client: AsyncClient, test_engine):
    """GET /corrections returns field_error_rates with correct counts."""
    headers = await _auth_headers(
        client, test_engine, email="ana-cor1@example.com", org_name="AnaCorOrg1"
    )
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    inv_id = await _insert_invoice(test_engine, org_id)
    await _insert_correction(test_engine, inv_id, org_id, user_id, field_name="invoice_number")
    await _insert_correction(test_engine, inv_id, org_id, user_id, field_name="invoice_number")
    await _insert_correction(test_engine, inv_id, org_id, user_id, field_name="total_amount")

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    rates = {row["field_name"]: row["correction_count"] for row in resp.json()["field_error_rates"]}
    assert rates.get("invoice_number") == 2
    assert rates.get("total_amount") == 1


async def test_corrections_error_rate_calculation(client: AsyncClient, test_engine):
    """GET /corrections error_rate = correction_count / invoice_count * 100."""
    headers = await _auth_headers(
        client, test_engine, email="ana-cor2@example.com", org_name="AnaCorOrg2"
    )
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    # Insert 2 invoices, 1 correction on field "seller"
    inv1 = await _insert_invoice(test_engine, org_id, invoice_number="C2-001")
    await _insert_invoice(test_engine, org_id, invoice_number="C2-002")
    await _insert_correction(test_engine, inv1, org_id, user_id, field_name="seller")

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    rates = resp.json()["field_error_rates"]
    seller_row = next((r for r in rates if r["field_name"] == "seller"), None)
    assert seller_row is not None
    assert seller_row["invoice_count"] == 2
    assert seller_row["correction_count"] == 1
    assert seller_row["error_rate"] == pytest.approx(50.0, abs=0.01)


async def test_corrections_high_confidence_errors(client: AsyncClient, test_engine):
    """GET /corrections high_confidence_errors counts corrections with confidence > 0.90."""
    headers = await _auth_headers(
        client, test_engine, email="ana-cor3@example.com", org_name="AnaCorOrg3"
    )
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    inv_id = await _insert_invoice(test_engine, org_id)
    # High-confidence correction (should appear)
    await _insert_correction(
        test_engine, inv_id, org_id, user_id, field_name="buyer", model_confidence=0.95
    )
    # Low-confidence correction (should NOT appear in high_confidence_errors)
    await _insert_correction(
        test_engine, inv_id, org_id, user_id, field_name="seller", model_confidence=0.50
    )

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    hce = resp.json()["high_confidence_errors"]
    hce_fields = {row["field_name"] for row in hce}
    assert "buyer" in hce_fields
    assert "seller" not in hce_fields


async def test_corrections_repeat_patterns(client: AsyncClient, test_engine):
    """GET /corrections repeat_patterns shows original→corrected pairs occurring 2+ times."""
    headers = await _auth_headers(
        client, test_engine, email="ana-cor4@example.com", org_name="AnaCorOrg4"
    )
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    inv1 = await _insert_invoice(test_engine, org_id, invoice_number="RP-001")
    inv2 = await _insert_invoice(test_engine, org_id, invoice_number="RP-002")

    # Same field + original → corrected twice
    await _insert_correction(
        test_engine,
        inv1,
        org_id,
        user_id,
        field_name="invoice_number",
        original_value="WRONG",
        corrected_value="RIGHT",
    )
    await _insert_correction(
        test_engine,
        inv2,
        org_id,
        user_id,
        field_name="invoice_number",
        original_value="WRONG",
        corrected_value="RIGHT",
    )
    # Unique correction (should not appear in patterns)
    await _insert_correction(
        test_engine,
        inv1,
        org_id,
        user_id,
        field_name="total_amount",
        original_value="BAD",
        corrected_value="GOOD",
    )

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    patterns = resp.json()["repeat_patterns"]
    matching = [
        p
        for p in patterns
        if p["field_name"] == "invoice_number"
        and p["original_value"] == "WRONG"
        and p["corrected_value"] == "RIGHT"
    ]
    assert len(matching) == 1
    assert matching[0]["occurrences"] == 2
    # Unique pattern should NOT appear
    unique = [p for p in patterns if p["field_name"] == "total_amount"]
    assert len(unique) == 0


async def test_corrections_org_isolation(client: AsyncClient, test_engine):
    """GET /corrections does not include data from other organizations."""
    headers_a = await _auth_headers(
        client, test_engine, email="ana-cor5a@example.com", org_name="AnaCorIsolA"
    )
    headers_b = await _auth_headers(
        client, test_engine, email="ana-cor5b@example.com", org_name="AnaCorIsolB"
    )
    org_id_b = _get_org_id(headers_b)
    user_id_b = _get_user_id(headers_b)

    inv_b = await _insert_invoice(test_engine, org_id_b)
    await _insert_correction(test_engine, inv_b, org_id_b, user_id_b, field_name="seller")

    # Org A has no corrections — should see empty lists
    resp = await client.get("/api/v1/analytics/corrections", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_error_rates"] == []
    assert data["high_confidence_errors"] == []


async def test_corrections_date_from_filter(client: AsyncClient, test_engine):
    """GET /corrections?date_from= excludes corrections created before the date."""
    from sqlalchemy import text as sa_text

    headers = await _auth_headers(
        client, test_engine, email="ana-cor6@example.com", org_name="AnaCorOrg6"
    )
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    inv_id = await _insert_invoice(test_engine, org_id)

    # Insert two corrections; backdate the first one to 2024
    await _insert_correction(
        test_engine, inv_id, org_id, user_id, field_name="buyer", model_confidence=0.80
    )
    sf = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        await db.execute(
            sa_text(
                "UPDATE correction_logs SET created_at = '2024-01-01T00:00:00+00:00' "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": org_id},
        )
        await db.commit()

    await _insert_correction(
        test_engine, inv_id, org_id, user_id, field_name="seller", model_confidence=0.70
    )

    # Filter from 2025 onwards — only the second correction should be visible
    resp = await client.get(
        "/api/v1/analytics/corrections?date_from=2025-01-01T00:00:00",
        headers=headers,
    )
    assert resp.status_code == 200
    rates = resp.json()["field_error_rates"]
    field_names = {r["field_name"] for r in rates}
    assert "seller" in field_names
    assert "buyer" not in field_names


async def test_corrections_date_to_filter(client: AsyncClient, test_engine):
    """GET /corrections?date_to= excludes corrections created after the date."""

    headers = await _auth_headers(
        client, test_engine, email="ana-cor7@example.com", org_name="AnaCorOrg7"
    )
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    inv_id = await _insert_invoice(test_engine, org_id)

    # Insert a recent correction
    await _insert_correction(test_engine, inv_id, org_id, user_id, field_name="invoice_number")

    # Filter to only show corrections up to 2020 — should return empty
    resp = await client.get(
        "/api/v1/analytics/corrections?date_to=2020-12-31T23:59:59",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_error_rates"] == []


async def test_corrections_response_schema(client: AsyncClient, test_engine):
    """GET /corrections response has the correct top-level keys."""
    headers = await _auth_headers(
        client, test_engine, email="ana-cor8@example.com", org_name="AnaCorOrg8"
    )
    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "field_error_rates" in data
    assert "high_confidence_errors" in data
    assert "repeat_patterns" in data
    assert isinstance(data["field_error_rates"], list)
    assert isinstance(data["high_confidence_errors"], list)
    assert isinstance(data["repeat_patterns"], list)
