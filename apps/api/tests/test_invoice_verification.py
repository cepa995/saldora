"""
Tests for mathematical verification, duplicate detection, and
verification endpoint integration (issues #29 and #32).

Unit tests for verify_calculations() and check_duplicates() run
against in-memory objects and mocked DB. API integration tests
exercise the POST /invoices/{id}/verify endpoint.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice
from app.services.invoice_verification import get_tolerance, verify_calculations

# ---- Helpers ----


async def _register_and_login(
    client: AsyncClient,
    email: str = "verify-test@example.com",
    password: str = "securepass123",
    first_name: str = "Verify",
    last_name: str = "Tester",
    org_name: str = "Verify Org",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
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
            invoice_number=overrides.get("invoice_number", "INV-001"),
            invoice_date=overrides.get("invoice_date", date(2026, 1, 15)),
            seller=overrides.get("seller", {"name": "Test Seller", "pib": "100000016"}),
            buyer=overrides.get("buyer"),
            subtotal=overrides.get("subtotal"),
            tax_rate=overrides.get("tax_rate"),
            tax_amount=overrides.get("tax_amount"),
            total_amount=overrides.get("total_amount", Decimal("1000.00")),
            line_items=overrides.get("line_items"),
            tax_groups=overrides.get("tax_groups"),
            document_path=overrides.get("document_path"),
            warnings=overrides.get("warnings"),
        )
        session.add(invoice)
        await session.commit()
        return str(invoice_id)


def _make_invoice(**kwargs) -> Invoice:
    """Create an in-memory Invoice object for unit testing (no DB)."""
    inv = Invoice()
    inv.id = uuid4()
    inv.organization_id = uuid4()
    inv.status = "review"
    inv.invoice_number = kwargs.get("invoice_number", "INV-001")
    inv.invoice_date = kwargs.get("invoice_date", date(2026, 1, 15))
    inv.seller = kwargs.get("seller", {"name": "Test", "pib": "100000016"})
    inv.buyer = kwargs.get("buyer")
    inv.subtotal = kwargs.get("subtotal")
    inv.tax_rate = kwargs.get("tax_rate")
    inv.tax_amount = kwargs.get("tax_amount")
    inv.total_amount = kwargs.get("total_amount", Decimal("1000.00"))
    inv.line_items = kwargs.get("line_items")
    inv.tax_groups = kwargs.get("tax_groups")
    return inv


# ---- Tolerance tests ----


def test_tolerance_small_amount():
    """Amounts up to 10,000 have ±1 RSD tolerance."""
    assert get_tolerance(Decimal("5000")) == Decimal("1")
    assert get_tolerance(Decimal("10000")) == Decimal("1")


def test_tolerance_medium_amount():
    """Amounts 10,001–100,000 have ±5 RSD tolerance."""
    assert get_tolerance(Decimal("10001")) == Decimal("5")
    assert get_tolerance(Decimal("100000")) == Decimal("5")


def test_tolerance_large_amount():
    """Amounts 100,001–1,000,000 have ±10 RSD tolerance."""
    assert get_tolerance(Decimal("100001")) == Decimal("10")
    assert get_tolerance(Decimal("1000000")) == Decimal("10")


def test_tolerance_very_large_amount():
    """Amounts over 1,000,000 have ±50 RSD tolerance."""
    assert get_tolerance(Decimal("1000001")) == Decimal("50")


# ---- Math verification unit tests ----


def test_correct_totals_no_warnings():
    """Correct subtotal + tax = total produces no warnings."""
    inv = _make_invoice(
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("12000.00"),
    )
    warnings = verify_calculations(inv)
    # Filter to only total_amount warnings
    total_warnings = [w for w in warnings if w["field_name"] == "total_amount"]
    assert len(total_warnings) == 0


def test_wrong_total_produces_warning():
    """Subtotal + tax ≠ total produces a warning."""
    inv = _make_invoice(
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("15000.00"),  # wrong: should be 12000
    )
    warnings = verify_calculations(inv)
    total_warnings = [w for w in warnings if w["field_name"] == "total_amount"]
    assert len(total_warnings) == 1
    assert "Zbir nije tačan" in total_warnings[0]["message"]


def test_tolerance_within_range_no_warning():
    """Difference within tolerance produces no warning."""
    inv = _make_invoice(
        subtotal=Decimal("5000.00"),
        tax_amount=Decimal("1000.00"),
        total_amount=Decimal("6000.50"),  # 0.50 diff, tolerance is ±1 for <10k
    )
    warnings = verify_calculations(inv)
    total_warnings = [w for w in warnings if w["field_name"] == "total_amount"]
    assert len(total_warnings) == 0


def test_tolerance_exceeded_produces_warning():
    """Difference beyond tolerance produces a warning."""
    inv = _make_invoice(
        subtotal=Decimal("5000.00"),
        tax_amount=Decimal("1000.00"),
        total_amount=Decimal("6002.00"),  # 2.00 diff, tolerance is ±1 for <10k
    )
    warnings = verify_calculations(inv)
    total_warnings = [w for w in warnings if w["field_name"] == "total_amount"]
    assert len(total_warnings) == 1


def test_line_items_sum_mismatch():
    """Line items not summing to subtotal produces a warning."""
    inv = _make_invoice(
        subtotal=Decimal("5000.00"),
        total_amount=Decimal("5000.00"),
        line_items=[
            {"description": "Item 1", "total": "3000.00"},
            {"description": "Item 2", "total": "1000.00"},
            # Sum = 4000, subtotal = 5000 → mismatch
        ],
    )
    warnings = verify_calculations(inv)
    subtotal_warnings = [w for w in warnings if w["field_name"] == "subtotal"]
    assert len(subtotal_warnings) == 1
    assert "Stavke se ne slažu" in subtotal_warnings[0]["message"]


def test_line_item_math_error():
    """Line item where qty × price ≠ total produces a warning."""
    inv = _make_invoice(
        total_amount=Decimal("5000.00"),
        line_items=[
            {
                "description": "Widget",
                "quantity": "10",
                "unit_price": "100.00",
                "total": "1500.00",  # should be 1000.00
            },
        ],
    )
    warnings = verify_calculations(inv)
    line_warnings = [w for w in warnings if w["field_name"] == "line_items"]
    assert len(line_warnings) == 1
    assert "Widget" in line_warnings[0]["message"]


def test_tax_groups_inconsistency():
    """Tax group sums not matching totals produces warnings."""
    inv = _make_invoice(
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("12000.00"),
        tax_groups=[
            {"rate": "20.00", "base_amount": "8000.00", "tax_amount": "1600.00"},
            # base sum = 8000 (expected 10000), tax sum = 1600 (expected 2000)
        ],
    )
    warnings = verify_calculations(inv)
    group_warnings = [w for w in warnings if w["field_name"] == "tax_groups"]
    assert len(group_warnings) == 2  # base mismatch + tax mismatch


def test_missing_fields_skipped():
    """No warnings when optional fields are null."""
    inv = _make_invoice(
        subtotal=None,
        tax_amount=None,
        total_amount=Decimal("1000.00"),
        line_items=None,
        tax_groups=None,
    )
    warnings = verify_calculations(inv)
    assert len(warnings) == 0


def test_line_items_correct_math():
    """Line items with correct math produce no warnings."""
    inv = _make_invoice(
        subtotal=Decimal("3000.00"),
        total_amount=Decimal("3000.00"),
        line_items=[
            {
                "description": "A",
                "quantity": "2",
                "unit_price": "1000.00",
                "total": "2000.00",
            },
            {
                "description": "B",
                "quantity": "1",
                "unit_price": "1000.00",
                "total": "1000.00",
            },
        ],
    )
    warnings = verify_calculations(inv)
    assert len(warnings) == 0


def test_vat_inclusive_line_items_no_warning():
    """Line items with VAT-inclusive prices sum to total_amount — no warning."""
    inv = _make_invoice(
        subtotal=Decimal("10482.58"),
        tax_amount=Decimal("2096.52"),
        total_amount=Decimal("12579.10"),
        line_items=[
            {"description": "FILTER KABINE", "total": "1639.50"},
            {"description": "FILTER ULJA", "total": "1111.50"},
            {"description": "Usluga servisa", "total": "9828.10"},
            # Sum = 12579.10 = total_amount (VAT-inclusive pricing)
        ],
    )
    warnings = verify_calculations(inv)
    subtotal_warnings = [w for w in warnings if w["field_name"] == "subtotal"]
    assert len(subtotal_warnings) == 0


def test_vat_inclusive_line_items_neither_match():
    """Line items that match neither subtotal nor total still produce a warning."""
    inv = _make_invoice(
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("12000.00"),
        line_items=[
            {"description": "Item", "total": "5000.00"},
            # Sum = 5000, doesn't match subtotal (10000) or total (12000)
        ],
    )
    warnings = verify_calculations(inv)
    subtotal_warnings = [w for w in warnings if w["field_name"] == "subtotal"]
    assert len(subtotal_warnings) == 1


# ---- Duplicate detection tests (API) ----


async def test_duplicate_detected(client: AsyncClient, test_engine):
    """Verifying an invoice with same number+date in org produces duplicate warning."""
    headers = await _register_and_login(client, email="dup-detect@example.com")
    org_id = _get_org_id(headers)

    # Insert two invoices with same number and date
    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="INV-DUP",
        invoice_date=date(2026, 3, 1),
        status="verified",
    )
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="INV-DUP",
        invoice_date=date(2026, 3, 1),
        status="review",
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    warning_messages = [w for w in data.get("warnings", []) if "duplikat" in w.lower()]
    assert len(warning_messages) >= 1


async def test_no_duplicate_different_number(client: AsyncClient, test_engine):
    """Different invoice numbers on same date do not trigger duplicate."""
    headers = await _register_and_login(client, email="dup-nodup@example.com")
    org_id = _get_org_id(headers)

    await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="INV-AAA",
        invoice_date=date(2026, 3, 1),
        status="verified",
    )
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        invoice_number="INV-BBB",
        invoice_date=date(2026, 3, 1),
        status="review",
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    warning_messages = [w for w in data.get("warnings", []) if "duplikat" in w.lower()]
    assert len(warning_messages) == 0


# ---- Verify endpoint integration tests ----


async def test_verify_adds_pib_warning(client: AsyncClient, test_engine):
    """Verifying invoice with invalid seller PIB adds a warning."""
    headers = await _register_and_login(client, email="vpib@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "Bad PIB Corp", "pib": "999999999"},
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    pib_warnings = [
        w for w in data.get("warnings", []) if "kontrolna cifra" in w.lower() or "pib" in w.lower()
    ]
    assert len(pib_warnings) >= 1


async def test_verify_adds_math_warning(client: AsyncClient, test_engine):
    """Verifying invoice with wrong math adds a calculation warning."""
    headers = await _register_and_login(client, email="vmath@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        subtotal=Decimal("5000.00"),
        tax_amount=Decimal("1000.00"),
        total_amount=Decimal("8000.00"),  # wrong: should be 6000
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    math_warnings = [
        w for w in data.get("warnings", []) if "zbir" in w.lower() or "tačan" in w.lower()
    ]
    assert len(math_warnings) >= 1


async def test_verify_succeeds_with_warnings(client: AsyncClient, test_engine):
    """Verification succeeds (status=verified) even when warnings are present."""
    headers = await _register_and_login(client, email="vwarn@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "Bad PIB", "pib": "111111111"},
        subtotal=Decimal("5000.00"),
        tax_amount=Decimal("1000.00"),
        total_amount=Decimal("9000.00"),  # wrong math + bad PIB
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert len(data.get("warnings", [])) >= 2  # at least PIB + math


async def test_verify_no_warnings_when_valid(client: AsyncClient, test_engine):
    """Clean invoice produces no verification warnings."""
    headers = await _register_and_login(client, email="vclean@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "Good Corp", "pib": "100000016"},
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("12000.00"),
    )

    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data.get("warnings", [])) == 0
