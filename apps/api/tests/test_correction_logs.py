"""
API tests for correction logging and analytics (issue #31).

Verifies that editing extracted invoice fields creates correction log
entries, and that the admin-only GET /api/v1/analytics/corrections
endpoint returns field error rates, high-confidence errors, and
repeat patterns with multi-tenant isolation.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.correction_log import CorrectionLog
from app.models.invoice import Invoice

# ---- Helpers ----


async def _register_and_login(
    client: AsyncClient,
    email: str = "correction-test@example.com",
    password: str = "securepass123",
    first_name: str = "Correction",
    last_name: str = "Tester",
    org_name: str = "Correction Org",
) -> dict[str, str]:
    """Register a user, log in, and return auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "organization_name": org_name,
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


def _get_user_id(headers: dict) -> str:
    """Extract user_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["sub"]


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB and return its id."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice_id = uuid4()
        invoice = Invoice(
            id=invoice_id,
            organization_id=org_id,
            status=overrides.get("status", "review"),
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2026, 1, 15)),
            seller=overrides.get("seller", {"name": "Test Seller", "pib": "123456789"}),
            total_amount=overrides.get("total_amount", Decimal("1000.00")),
            document_path=overrides.get("document_path"),
            field_confidence=overrides.get("field_confidence"),
        )
        session.add(invoice)
        await session.commit()
        return str(invoice_id)


async def _get_correction_logs(test_engine, org_id: str | None = None) -> list[CorrectionLog]:
    """Fetch correction log entries from the DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        query = select(CorrectionLog).order_by(CorrectionLog.created_at.desc())
        if org_id:
            query = query.where(CorrectionLog.organization_id == org_id)
        result = await session.execute(query)
        return list(result.scalars().all())


async def _insert_correction_log(test_engine, org_id: str, **overrides) -> None:
    """Insert a correction log entry directly into the DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        entry = CorrectionLog(
            invoice_id=overrides.get("invoice_id", uuid4()),
            organization_id=org_id,
            user_id=overrides.get("user_id", uuid4()),
            field_name=overrides.get("field_name", "invoice_number"),
            original_value=overrides.get("original_value", "INV-001"),
            corrected_value=overrides.get("corrected_value", "INV-002"),
            model_confidence=overrides.get("model_confidence"),
            correction_type=overrides.get("correction_type"),
        )
        session.add(entry)
        await session.commit()


# ---- Correction logging tests ----


async def test_update_creates_correction_log(client: AsyncClient, test_engine):
    """Editing an invoice field creates a correction log entry."""
    headers = await _register_and_login(client, email="corr-basic@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers,
        json={"invoice_number": "INV-CORRECTED"},
    )

    logs = await _get_correction_logs(test_engine, org_id=org_id)
    corr_logs = [entry for entry in logs if entry.field_name == "invoice_number"]
    assert len(corr_logs) >= 1
    assert corr_logs[0].original_value == "INV-001"
    assert corr_logs[0].corrected_value == "INV-CORRECTED"
    assert str(corr_logs[0].invoice_id) == invoice_id


async def test_correction_captures_model_confidence(client: AsyncClient, test_engine):
    """Correction log captures model confidence from field_confidence list."""
    headers = await _register_and_login(client, email="corr-conf@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        field_confidence=[
            {
                "field_name": "invoice_number",
                "value": "INV-001",
                "confidence": 0.95,
                "needs_review": False,
            },
        ],
    )

    await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers,
        json={"invoice_number": "INV-FIXED"},
    )

    logs = await _get_correction_logs(test_engine, org_id=org_id)
    corr_logs = [entry for entry in logs if entry.field_name == "invoice_number"]
    assert len(corr_logs) >= 1
    assert float(corr_logs[0].model_confidence) == 0.95


async def test_correction_multiple_fields(client: AsyncClient, test_engine):
    """Editing multiple fields creates one correction entry per field."""
    headers = await _register_and_login(client, email="corr-multi@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        total_amount=Decimal("1000.00"),
    )

    await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers,
        json={
            "invoice_number": "INV-MULTI",
            "total_amount": "2000.00",
        },
    )

    logs = await _get_correction_logs(test_engine, org_id=org_id)
    field_names = {entry.field_name for entry in logs}
    assert "invoice_number" in field_names
    assert "total_amount" in field_names


async def test_no_correction_when_value_unchanged(client: AsyncClient, test_engine):
    """No correction log when the submitted value equals the existing one."""
    headers = await _register_and_login(client, email="corr-noop@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id, invoice_number="INV-SAME")

    await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=headers,
        json={"invoice_number": "INV-SAME"},
    )

    logs = await _get_correction_logs(test_engine, org_id=org_id)
    corr_logs = [entry for entry in logs if entry.field_name == "invoice_number"]
    assert len(corr_logs) == 0


# ---- Analytics endpoint tests ----


async def test_analytics_field_error_rate(client: AsyncClient, test_engine):
    """Analytics endpoint returns field error rates."""
    headers = await _register_and_login(client, email="ana-rate@example.com")
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    # Create an invoice and a correction
    invoice_id = await _insert_invoice(test_engine, org_id)
    await _insert_correction_log(
        test_engine,
        org_id,
        invoice_id=invoice_id,
        user_id=user_id,
        field_name="invoice_number",
        original_value="INV-001",
        corrected_value="INV-FIXED",
    )

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "field_error_rates" in data
    rates = data["field_error_rates"]
    assert len(rates) >= 1
    inv_rate = next((r for r in rates if r["field_name"] == "invoice_number"), None)
    assert inv_rate is not None
    assert inv_rate["correction_count"] >= 1
    assert inv_rate["error_rate"] > 0


async def test_analytics_high_confidence_errors(client: AsyncClient, test_engine):
    """Analytics endpoint returns high-confidence errors (confidence > 90%)."""
    headers = await _register_and_login(client, email="ana-hce@example.com")
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    invoice_id = await _insert_invoice(test_engine, org_id)
    await _insert_correction_log(
        test_engine,
        org_id,
        invoice_id=invoice_id,
        user_id=user_id,
        field_name="total_amount",
        original_value="1000.00",
        corrected_value="2000.00",
        model_confidence=0.95,
    )

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    hce = data["high_confidence_errors"]
    assert len(hce) >= 1
    assert any(entry["field_name"] == "total_amount" for entry in hce)


async def test_analytics_repeat_patterns(client: AsyncClient, test_engine):
    """Analytics endpoint returns repeat error patterns (occurrences > 1)."""
    headers = await _register_and_login(client, email="ana-repeat@example.com")
    org_id = _get_org_id(headers)
    user_id = _get_user_id(headers)

    invoice_id_1 = await _insert_invoice(test_engine, org_id, invoice_number="INV-A")
    invoice_id_2 = await _insert_invoice(test_engine, org_id, invoice_number="INV-B")

    # Same correction pattern twice
    for inv_id in [invoice_id_1, invoice_id_2]:
        await _insert_correction_log(
            test_engine,
            org_id,
            invoice_id=inv_id,
            user_id=user_id,
            field_name="seller_pib",
            original_value="12345678",
            corrected_value="123456789",
        )

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    patterns = data["repeat_patterns"]
    assert len(patterns) >= 1
    match = next(
        (
            p
            for p in patterns
            if p["field_name"] == "seller_pib" and p["original_value"] == "12345678"
        ),
        None,
    )
    assert match is not None
    assert match["occurrences"] >= 2


async def test_analytics_admin_only(client: AsyncClient, test_engine):
    """Non-admin users get 403 when accessing correction analytics."""
    headers = await _register_and_login(client, email="ana-nonadm@example.com")
    user_id = _get_user_id(headers)

    # Downgrade to member
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE users SET role = 'member' WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()

    resp = await client.get("/api/v1/analytics/corrections", headers=headers)
    assert resp.status_code == 403


async def test_analytics_org_isolation(client: AsyncClient, test_engine):
    """Admin can only see correction data from their own organization."""
    headers_a = await _register_and_login(
        client, email="ana-iso-a@example.com", org_name="Iso Org A"
    )
    headers_b = await _register_and_login(
        client, email="ana-iso-b@example.com", org_name="Iso Org B"
    )
    org_b_id = _get_org_id(headers_b)
    user_b_id = _get_user_id(headers_b)

    # Create correction in Org B
    invoice_id = await _insert_invoice(test_engine, org_b_id, invoice_number="INV-ISO")
    await _insert_correction_log(
        test_engine,
        org_b_id,
        invoice_id=invoice_id,
        user_id=user_b_id,
        field_name="invoice_number",
        original_value="INV-ISO",
        corrected_value="INV-FIXED",
    )

    # Org A should NOT see Org B's corrections
    resp = await client.get("/api/v1/analytics/corrections", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    # Org A has no corrections, so field_error_rates should be empty
    assert len(data["field_error_rates"]) == 0
