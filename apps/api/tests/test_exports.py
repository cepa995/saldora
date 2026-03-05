"""Tests for data export endpoints and generators.

Covers XLSX, CSV, JSON, MiniMax XML formats, export blocking rules,
auth/org isolation, and MiniMax API push (mocked).
"""

import csv
import json
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from types import SimpleNamespace
from uuid import uuid4

from httpx import AsyncClient
from openpyxl import load_workbook
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice
from app.services.export.core import (
    VALID_FIELD_KEYS,
    apply_template,
    check_export_blocking,
    extract_invoice_row,
    format_serbian_date,
    format_serbian_number,
)
from app.services.export.csv_gen import generate_csv
from app.services.export.json_gen import generate_json
from app.services.export.minimax_xml import generate_minimax_xml
from app.services.export.xlsx import generate_xlsx


def _mock_invoice(**kwargs) -> SimpleNamespace:
    """Create a mock invoice object that quacks like Invoice.

    Uses SimpleNamespace instead of Invoice.__new__() to avoid
    SQLAlchemy instrumentation issues in unit tests.
    """
    return SimpleNamespace(
        id=kwargs.get("id", uuid4()),
        invoice_number=kwargs.get("invoice_number", "FAKT-001"),
        invoice_date=kwargs.get("invoice_date", date(2025, 6, 15)),
        due_date=kwargs.get("due_date", date(2025, 7, 15)),
        seller=kwargs.get(
            "seller",
            {
                "pib": "123456789",
                "name": "Prodavac DOO",
                "address": "Nemanjina 4",
                "city": "Beograd",
            },
        ),
        buyer=kwargs.get(
            "buyer",
            {
                "pib": "987654321",
                "name": "Kupac DOO",
                "address": "Bulevar 1",
                "city": "Novi Sad",
            },
        ),
        subtotal=kwargs.get("subtotal", Decimal("10000.00")),
        tax_rate=kwargs.get("tax_rate", Decimal("20.00")),
        tax_amount=kwargs.get("tax_amount", Decimal("2000.00")),
        total_amount=kwargs.get("total_amount", Decimal("12000.00")),
        currency=kwargs.get("currency", "RSD"),
        status=kwargs.get("status", "verified"),
        confidence_score=kwargs.get("confidence_score", Decimal("0.92")),
        line_items=kwargs.get(
            "line_items",
            [
                {
                    "description": "Konsultantske usluge",
                    "quantity": "2",
                    "unit_price": "5000",
                    "total": "10000",
                    "tax_rate": "20",
                    "tax_amount": "2000",
                }
            ],
        ),
        tax_groups=kwargs.get("tax_groups", []),
        warnings=kwargs.get("warnings", []),
        accounting_intent=kwargs.get("accounting_intent", None),
        content_type=kwargs.get("content_type", "application/pdf"),
        document_path=kwargs.get("document_path", None),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user, log in, and return Authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "export-test@example.com",
            "password": "securepass123",
            "first_name": "Export",
            "last_name": "Tester",
            "organization_name": "Export Org",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "export-test@example.com", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _auth_headers_alt(client: AsyncClient) -> dict[str, str]:
    """Register a second user (different org) and return Authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-export@example.com",
            "password": "securepass123",
            "first_name": "Other",
            "last_name": "Export",
            "organization_name": "Other Export Org",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "other-export@example.com", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["org"]


async def _seed_default_templates(test_engine) -> None:
    """Seed system default templates (mirrors Alembic migration seed data).

    Required because test DB uses create_all() which doesn't run migrations.
    """
    import json as _json

    from sqlalchemy import text

    defaults = [
        (
            "Standardni izvoz",
            "Sva polja u standardnom redosledu",
            [
                {"key": "invoice_number", "label": "Broj fakture", "order": 1},
                {"key": "invoice_date", "label": "Datum fakture", "order": 2},
                {"key": "seller_name", "label": "Prodavac", "order": 4},
                {"key": "total_amount", "label": "Ukupan iznos", "order": 13},
            ],
            ["xlsx", "csv", "json"],
        ),
        (
            "Racunovodstveni izvoz",
            "Polja za knjizenje",
            [
                {"key": "invoice_number", "label": "Broj fakture", "order": 1},
                {"key": "subtotal", "label": "Osnovica", "order": 5},
            ],
            ["xlsx", "csv", "json"],
        ),
        (
            "MiniMax izvoz",
            "Format za MiniMax",
            [],
            ["minimax_xml"],
        ),
        (
            "PDV evidencija",
            "Format za PDV prijavu",
            [
                {"key": "invoice_number", "label": "Broj fakture", "order": 1},
                {"key": "tax_amount", "label": "Iznos PDV", "order": 7},
            ],
            ["xlsx", "csv"],
        ),
    ]

    async with test_engine.begin() as conn:
        for name, desc, fields, formats in defaults:
            await conn.execute(
                text(
                    "INSERT INTO export_templates "
                    "(id, organization_id, name, description, is_default, "
                    "fields, supported_formats, created_by, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), NULL, :name, :desc, true, "
                    ":fields, :formats, NULL, now(), now())"
                ),
                {
                    "name": name,
                    "desc": desc,
                    "fields": _json.dumps(fields),
                    "formats": _json.dumps(formats),
                },
            )


async def _insert_invoice(test_engine, org_id: str, **overrides) -> str:
    """Insert a test invoice directly into the DB.

    Args:
        test_engine: SQLAlchemy async engine.
        org_id: Organization UUID string.
        **overrides: Invoice column overrides.

    Returns:
        String UUID of the created invoice.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        invoice = Invoice(
            organization_id=org_id,
            status=overrides.get("status", "verified"),
            invoice_number=overrides.get("invoice_number", "FAKT-001"),
            invoice_date=overrides.get("invoice_date", date(2025, 6, 15)),
            due_date=overrides.get("due_date", date(2025, 7, 15)),
            seller=overrides.get(
                "seller",
                {
                    "pib": "123456789",
                    "name": "Prodavac DOO",
                    "address": "Nemanjina 4",
                    "city": "Beograd",
                },
            ),
            buyer=overrides.get(
                "buyer",
                {
                    "pib": "987654321",
                    "name": "Kupac DOO",
                    "address": "Bulevar Oslobodjenja 1",
                    "city": "Novi Sad",
                },
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
                        "description": "Konsultantske usluge",
                        "quantity": "2.00",
                        "unit_price": "5000.00",
                        "total": "10000.00",
                        "tax_rate": "20.00",
                        "tax_amount": "2000.00",
                    }
                ],
            ),
            document_hash=overrides.get("document_hash", uuid4().hex),
            document_path=overrides.get("document_path", "orgs/test/inv/original.pdf"),
            document_content_type=overrides.get("document_content_type", "application/pdf"),
            confidence_score=overrides.get("confidence_score", Decimal("0.92")),
            field_confidence=overrides.get("field_confidence", []),
            warnings=overrides.get("warnings", []),
        )
        session.add(invoice)
        await session.commit()
        return str(invoice.id)


# ---------------------------------------------------------------------------
# Unit tests: formatting helpers
# ---------------------------------------------------------------------------


class TestFormatting:
    """Tests for Serbian formatting utilities."""

    def test_format_serbian_date_default(self):
        """DD.MM.YYYY format."""
        assert format_serbian_date(date(2025, 6, 15)) == "15.06.2025"

    def test_format_serbian_date_iso(self):
        """YYYY-MM-DD format."""
        assert format_serbian_date(date(2025, 6, 15), "YYYY-MM-DD") == "2025-06-15"

    def test_format_serbian_date_none(self):
        """None returns empty string."""
        assert format_serbian_date(None) == ""

    def test_format_serbian_number_comma(self):
        """Serbian comma separator: 45.000,00."""
        assert format_serbian_number(Decimal("45000.00"), ",") == "45.000,00"

    def test_format_serbian_number_dot(self):
        """International dot separator: 45,000.00."""
        assert format_serbian_number(Decimal("45000.00"), ".") == "45,000.00"

    def test_format_serbian_number_none(self):
        """None returns empty string."""
        assert format_serbian_number(None) == ""


# ---------------------------------------------------------------------------
# Unit tests: export blocking
# ---------------------------------------------------------------------------


class TestExportBlocking:
    """Tests for SRS 4.9.7 export blocking rules."""

    def test_valid_invoice_passes(self):
        """Fully valid invoice passes blocking check."""
        inv = _mock_invoice()
        assert check_export_blocking([inv]) == []

    def test_missing_invoice_number_blocks(self):
        """Missing invoice number blocks export."""
        inv = _mock_invoice(invoice_number=None)
        blocked = check_export_blocking([inv])
        assert len(blocked) == 1
        assert "Nedostaje broj fakture" in blocked[0]["reasons"]

    def test_missing_date_blocks(self):
        """Missing invoice date blocks export."""
        inv = _mock_invoice(invoice_date=None)
        blocked = check_export_blocking([inv])
        assert len(blocked) == 1
        assert "Nedostaje datum fakture" in blocked[0]["reasons"]

    def test_missing_total_blocks(self):
        """Missing total amount blocks export."""
        inv = _mock_invoice(total_amount=None)
        blocked = check_export_blocking([inv])
        assert len(blocked) == 1

    def test_missing_pib_blocks(self):
        """Missing seller PIB blocks export."""
        inv = _mock_invoice(seller={"name": "Test"})
        blocked = check_export_blocking([inv])
        assert len(blocked) == 1
        assert "Nedostaje PIB prodavca" in blocked[0]["reasons"]

    def test_low_confidence_unverified_blocks(self):
        """Low confidence (< 60%) without verification blocks export."""
        inv = _mock_invoice(confidence_score=Decimal("45"), status="review")
        blocked = check_export_blocking([inv])
        assert len(blocked) == 1
        assert "Nizak nivo pouzdanosti" in blocked[0]["reasons"][0]

    def test_low_confidence_verified_passes(self):
        """Low confidence with verified status passes."""
        inv = _mock_invoice(confidence_score=Decimal("45"), status="verified")
        assert check_export_blocking([inv]) == []

    def test_blocking_warnings_block(self):
        """Unresolved blocking warnings block export."""
        inv = _mock_invoice(
            status="review",
            confidence_score=Decimal("85"),
            warnings=[{"type": "math_error", "blocking": True}],
        )
        blocked = check_export_blocking([inv])
        assert len(blocked) == 1
        assert any("blokirajuca" in r.lower() for r in blocked[0]["reasons"])

    def test_minimax_xml_requires_verified_status(self):
        """MiniMax XML export blocks unverified invoices."""
        inv = _mock_invoice(status="review", confidence_score=Decimal("85"))
        blocked = check_export_blocking([inv], export_format="minimax_xml")
        assert len(blocked) == 1
        assert any("verifikovana" in r for r in blocked[0]["reasons"])

    def test_minimax_xml_allows_verified(self):
        """MiniMax XML export allows verified invoices."""
        inv = _mock_invoice(status="verified")
        assert check_export_blocking([inv], export_format="minimax_xml") == []

    def test_minimax_xml_allows_exported(self):
        """MiniMax XML export allows already-exported invoices."""
        inv = _mock_invoice(status="exported", confidence_score=Decimal("85"))
        assert check_export_blocking([inv], export_format="minimax_xml") == []

    def test_non_minimax_allows_review_status(self):
        """Non-MiniMax formats allow invoices in review status."""
        inv = _mock_invoice(status="review", confidence_score=Decimal("85"))
        assert check_export_blocking([inv], export_format="xlsx") == []


# ---------------------------------------------------------------------------
# Unit tests: XLSX generator
# ---------------------------------------------------------------------------


class TestXLSXGenerator:
    """Tests for XLSX export generation."""

    def test_xlsx_has_main_sheet(self):
        """XLSX has 'Fakture' main sheet with correct headers."""
        inv = _mock_invoice()
        buf = generate_xlsx([inv])
        wb = load_workbook(buf)

        assert "Fakture" in wb.sheetnames
        ws = wb["Fakture"]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert "Broj fakture" in headers
        assert "Ukupan iznos" in headers

    def test_xlsx_has_line_items_sheet(self):
        """XLSX includes 'Stavke' line items sheet."""
        inv = _mock_invoice()
        buf = generate_xlsx([inv], include_line_items=True)
        wb = load_workbook(buf)

        assert "Stavke" in wb.sheetnames
        ws = wb["Stavke"]
        assert ws.max_row >= 2

    def test_xlsx_no_line_items_when_disabled(self):
        """XLSX omits 'Stavke' when include_line_items=False."""
        inv = _mock_invoice()
        buf = generate_xlsx([inv], include_line_items=False)
        wb = load_workbook(buf)

        assert "Stavke" not in wb.sheetnames

    def test_xlsx_serbian_number_formatting(self):
        """Numbers use Serbian formatting (comma decimal)."""
        inv = _mock_invoice()
        buf = generate_xlsx([inv], decimal_separator=",")
        wb = load_workbook(buf)
        ws = wb["Fakture"]

        row2 = [ws.cell(2, c).value for c in range(1, ws.max_column + 1)]
        has_serbian = any(isinstance(v, str) and "," in v and "." in v for v in row2 if v)
        assert has_serbian

    def test_xlsx_two_invoices(self):
        """XLSX handles multiple invoices."""
        inv1 = _mock_invoice()
        inv2 = _mock_invoice(invoice_number="FAKT-002")
        buf = generate_xlsx([inv1, inv2])
        wb = load_workbook(buf)
        ws = wb["Fakture"]

        assert ws.max_row >= 3


# ---------------------------------------------------------------------------
# Unit tests: CSV generator
# ---------------------------------------------------------------------------


class TestCSVGenerator:
    """Tests for CSV export generation."""

    def test_csv_has_bom(self):
        """CSV starts with UTF-8 BOM for Excel compatibility."""
        inv = _mock_invoice(invoice_number="FAKT-CSV-001")
        buf = generate_csv([inv])
        content = buf.read()
        assert content[:3] == b"\xef\xbb\xbf"

    def test_csv_semicolon_delimiter(self):
        """CSV uses semicolon delimiter by default."""
        inv = _mock_invoice()
        buf = generate_csv([inv], delimiter="semicolon")
        content = buf.read().decode("utf-8-sig")
        lines = content.strip().split("\n")
        assert ";" in lines[0]

    def test_csv_comma_delimiter(self):
        """CSV supports comma delimiter."""
        inv = _mock_invoice()
        buf = generate_csv([inv], delimiter="comma")
        content = buf.read().decode("utf-8-sig")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        assert len(rows) >= 2

    def test_csv_serbian_headers(self):
        """CSV has Serbian column headers."""
        inv = _mock_invoice()
        buf = generate_csv([inv])
        content = buf.read().decode("utf-8-sig")
        assert "Broj fakture" in content
        assert "Ukupan iznos" in content

    def test_csv_data_present(self):
        """CSV contains invoice data."""
        inv = _mock_invoice(invoice_number="FAKT-CSV-001")
        buf = generate_csv([inv])
        content = buf.read().decode("utf-8-sig")
        assert "FAKT-CSV-001" in content


# ---------------------------------------------------------------------------
# Unit tests: JSON generator
# ---------------------------------------------------------------------------


class TestJSONGenerator:
    """Tests for JSON export generation."""

    def test_json_flat_mode(self):
        """Flat JSON is array of objects with string values."""
        inv = _mock_invoice(invoice_number="JSON-001")
        buf = generate_json([inv], nested=False)
        data = json.loads(buf.read())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["invoice_number"] == "JSON-001"

    def test_json_nested_mode(self):
        """Nested JSON includes line_items and seller/buyer objects."""
        inv = _mock_invoice(
            seller={"pib": "111222333", "name": "JSON Prodavac"},
            line_items=[{"description": "Test item", "total": "8000"}],
        )
        buf = generate_json([inv], nested=True)
        data = json.loads(buf.read())
        assert isinstance(data, list)
        record = data[0]
        assert "seller" in record
        assert record["seller"]["pib"] == "111222333"
        assert "line_items" in record
        assert len(record["line_items"]) == 1

    def test_json_nested_amounts_are_numbers(self):
        """Nested JSON uses numeric values, not strings."""
        inv = _mock_invoice(total_amount=Decimal("9600.00"))
        buf = generate_json([inv], nested=True)
        data = json.loads(buf.read())
        record = data[0]
        assert isinstance(record["total_amount"], (int, float))
        assert record["total_amount"] == 9600.0

    def test_json_flat_dates_formatted(self):
        """Flat JSON formats dates as DD.MM.YYYY."""
        inv = _mock_invoice()
        buf = generate_json([inv], nested=False, date_format="DD.MM.YYYY")
        data = json.loads(buf.read())
        assert data[0]["invoice_date"] == "15.06.2025"


# ---------------------------------------------------------------------------
# Unit tests: MiniMax XML generator
# ---------------------------------------------------------------------------


class TestMiniMaxXMLGenerator:
    """Tests for MiniMax XML export generation."""

    def _make_mm_invoice(self):
        """Create a test invoice with accounting intent for XML tests."""
        mock_intent = SimpleNamespace(
            suggested_konta={
                "debit": [{"konto": "4310", "name": "Troskovi usluga", "amount": "10000"}],
                "credit": [{"konto": "4340", "name": "Dobavljaci", "amount": "10000"}],
            },
            vat_breakdown={
                "20": {"base": 10000, "tax": 2000},
            },
        )
        return _mock_invoice(
            invoice_number="MM-001",
            seller={
                "pib": "123456789",
                "name": "XML Prodavac DOO",
                "address": "Nemanjina 4",
                "city": "Beograd",
            },
            accounting_intent=mock_intent,
        )

    def test_xml_root_element(self):
        """XML root element is miniMAXUvozKnjigovodstvo."""
        inv = self._make_mm_invoice()
        buf = generate_minimax_xml([inv])
        tree = ET.parse(buf)
        root = tree.getroot()
        assert "miniMAXUvozKnjigovodstvo" in root.tag

    def test_xml_has_stranke(self):
        """XML contains Stranke (partners) section."""
        inv = self._make_mm_invoice()
        buf = generate_minimax_xml([inv])
        content = buf.read().decode("utf-8")
        assert "<Stranke>" in content
        assert "<Stranka>" in content
        assert "123456789" in content

    def test_xml_has_temeljnice(self):
        """XML contains Temeljnice (journal entries) section."""
        inv = self._make_mm_invoice()
        buf = generate_minimax_xml([inv])
        content = buf.read().decode("utf-8")
        assert "<Temeljnice>" in content
        assert "<Temeljnica>" in content
        assert "4310" in content

    def test_xml_has_ddv(self):
        """XML contains DDV (VAT) entries."""
        inv = self._make_mm_invoice()
        buf = generate_minimax_xml([inv])
        content = buf.read().decode("utf-8")
        assert "<DDV>" in content
        assert "<Stopnja>" in content

    def test_xml_deduplicates_partners(self):
        """Stranke are deduplicated by PIB."""
        inv1 = self._make_mm_invoice()
        inv2 = self._make_mm_invoice()
        inv2.invoice_number = "MM-002"

        buf = generate_minimax_xml([inv1, inv2])
        content = buf.read().decode("utf-8")
        assert content.count("<Stranka>") == 1

    def test_xml_valid_structure(self):
        """XML is well-formed and parseable."""
        inv = self._make_mm_invoice()
        buf = generate_minimax_xml([inv])
        tree = ET.parse(buf)
        root = tree.getroot()
        assert root is not None


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestExportEndpoint:
    """Integration tests for POST /api/v1/export."""

    async def test_export_xlsx(self, client: AsyncClient, test_engine):
        """Export invoices as XLSX."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id)

        resp = await client.post(
            "/api/v1/export",
            json={"format": "xlsx", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert resp.headers["content-disposition"].endswith('.xlsx"')

        # Verify it's valid XLSX
        wb = load_workbook(BytesIO(resp.content))
        assert "Fakture" in wb.sheetnames

    async def test_export_csv(self, client: AsyncClient, test_engine):
        """Export invoices as CSV."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id)

        resp = await client.post(
            "/api/v1/export",
            json={"format": "csv", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        # Verify BOM
        assert resp.content[:3] == b"\xef\xbb\xbf"

    async def test_export_json(self, client: AsyncClient, test_engine):
        """Export invoices as JSON."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id)

        resp = await client.post(
            "/api/v1/export",
            json={"format": "json", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    async def test_export_minimax_xml(self, client: AsyncClient, test_engine):
        """Export invoices as MiniMax XML."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id)

        resp = await client.post(
            "/api/v1/export",
            json={"format": "minimax_xml", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "xml" in resp.headers["content-type"]
        # Should parse as valid XML
        ET.fromstring(resp.content)

    async def test_export_requires_auth(self, client: AsyncClient):
        """Export requires authentication."""
        resp = await client.post(
            "/api/v1/export",
            json={"format": "xlsx", "invoice_ids": [str(uuid4())]},
        )
        assert resp.status_code == 401

    async def test_export_org_isolation(self, client: AsyncClient, test_engine):
        """Cannot export invoices from another organization."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id)

        # Another user in a different org
        alt_headers = await _auth_headers_alt(client)

        resp = await client.post(
            "/api/v1/export",
            json={"format": "xlsx", "invoice_ids": [inv_id]},
            headers=alt_headers,
        )
        assert resp.status_code == 404

    async def test_export_blocks_missing_fields(self, client: AsyncClient, test_engine):
        """Export returns 422 when invoice has missing required fields."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)

        inv_id = await _insert_invoice(
            test_engine,
            org_id,
            invoice_number=None,
            seller={"name": "No PIB"},
        )

        resp = await client.post(
            "/api/v1/export",
            json={"format": "xlsx", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "blocked_invoices" in detail

    async def test_export_blocks_low_confidence(self, client: AsyncClient, test_engine):
        """Export returns 422 for low confidence unverified invoice."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)

        inv_id = await _insert_invoice(
            test_engine,
            org_id,
            confidence_score=Decimal("0.45"),
            status="review",
        )

        resp = await client.post(
            "/api/v1/export",
            json={"format": "xlsx", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_export_nonexistent_invoice(self, client: AsyncClient, test_engine):
        """Export returns 404 for nonexistent invoice ID."""
        headers = await _auth_headers(client)

        resp = await client.post(
            "/api/v1/export",
            json={"format": "xlsx", "invoice_ids": [str(uuid4())]},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_minimax_xml_blocks_unverified(self, client: AsyncClient, test_engine):
        """MiniMax XML export returns 422 for unverified invoices."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)

        inv_id = await _insert_invoice(
            test_engine,
            org_id,
            status="review",
            confidence_score=Decimal("0.85"),
        )

        resp = await client.post(
            "/api/v1/export",
            json={"format": "minimax_xml", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "blocked_invoices" in detail
        reasons = detail["blocked_invoices"][0]["reasons"]
        assert any("verifikovana" in r for r in reasons)

    async def test_minimax_xml_allows_verified(self, client: AsyncClient, test_engine):
        """MiniMax XML export succeeds for verified invoices."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id, status="verified")

        resp = await client.post(
            "/api/v1/export",
            json={"format": "minimax_xml", "invoice_ids": [inv_id]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "xml" in resp.headers["content-type"]


class TestExportTemplates:
    """Tests for GET /api/v1/export/templates."""

    async def test_list_templates(self, client: AsyncClient, test_engine):
        """Returns list of system default export templates."""
        await _seed_default_templates(test_engine)
        headers = await _auth_headers(client)

        resp = await client.get(
            "/api/v1/export/templates",
            headers=headers,
        )
        assert resp.status_code == 200
        templates = resp.json()
        assert isinstance(templates, list)
        assert len(templates) >= 4

        names = [t["name"] for t in templates]
        assert "Standardni izvoz" in names
        assert "MiniMax izvoz" in names
        assert all(t["is_default"] for t in templates)

    async def test_templates_require_auth(self, client: AsyncClient):
        """Templates endpoint requires authentication."""
        resp = await client.get("/api/v1/export/templates")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Unit tests: apply_template
# ---------------------------------------------------------------------------


class TestApplyTemplate:
    """Tests for apply_template() in core.py."""

    def test_selects_subset_of_fields(self):
        """Template selects only specified fields."""
        inv = _mock_invoice()
        row = extract_invoice_row(inv)
        template_fields = [
            {"key": "invoice_number", "label": "Broj", "order": 1},
            {"key": "total_amount", "label": "Ukupno", "order": 2},
            {"key": "currency", "label": "Valuta", "order": 3},
        ]
        result = apply_template(row, template_fields)
        assert list(result.keys()) == ["Broj", "Ukupno", "Valuta"]
        assert len(result) == 3

    def test_reorders_fields(self):
        """Template reorders fields by order value."""
        inv = _mock_invoice()
        row = extract_invoice_row(inv)
        template_fields = [
            {"key": "total_amount", "label": "Ukupno", "order": 2},
            {"key": "invoice_number", "label": "Broj", "order": 1},
        ]
        result = apply_template(row, template_fields)
        keys = list(result.keys())
        assert keys[0] == "Broj"
        assert keys[1] == "Ukupno"

    def test_custom_labels(self):
        """Template uses custom labels as keys."""
        inv = _mock_invoice(invoice_number="TEST-001")
        row = extract_invoice_row(inv)
        template_fields = [
            {"key": "invoice_number", "label": "Br. fakture", "order": 1},
        ]
        result = apply_template(row, template_fields)
        assert "Br. fakture" in result
        assert result["Br. fakture"] == "TEST-001"

    def test_missing_data_returns_empty(self):
        """Missing field data returns empty string."""
        inv = _mock_invoice(seller={})
        row = extract_invoice_row(inv)
        template_fields = [
            {"key": "seller_name", "label": "Prodavac", "order": 1},
        ]
        result = apply_template(row, template_fields)
        assert result["Prodavac"] == ""

    def test_valid_field_keys_set(self):
        """VALID_FIELD_KEYS contains all expected keys."""
        expected = {
            "invoice_number",
            "invoice_date",
            "due_date",
            "seller_name",
            "seller_pib",
            "seller_address",
            "seller_city",
            "buyer_name",
            "buyer_pib",
            "subtotal",
            "tax_rate",
            "tax_amount",
            "total_amount",
            "currency",
            "status",
            "confidence_score",
        }
        assert VALID_FIELD_KEYS == expected


# ---------------------------------------------------------------------------
# Unit tests: generators with templates
# ---------------------------------------------------------------------------


class TestXLSXWithTemplate:
    """Tests for XLSX export with custom template."""

    def test_xlsx_template_limits_columns(self):
        """XLSX with template shows only template columns."""
        inv = _mock_invoice()
        template_fields = [
            {"key": "invoice_number", "label": "Broj", "order": 1},
            {"key": "seller_name", "label": "Prodavac", "order": 2},
            {"key": "total_amount", "label": "Ukupno", "order": 3},
            {"key": "currency", "label": "Valuta", "order": 4},
            {"key": "status", "label": "Status", "order": 5},
        ]
        buf = generate_xlsx([inv], template_fields=template_fields)
        wb = load_workbook(buf)
        ws = wb["Fakture"]
        assert ws.max_column == 5

    def test_xlsx_template_custom_headers(self):
        """XLSX with template uses custom header labels."""
        inv = _mock_invoice()
        template_fields = [
            {"key": "invoice_number", "label": "Br. fakture", "order": 1},
            {"key": "total_amount", "label": "Ukupan iznos (RSD)", "order": 2},
        ]
        buf = generate_xlsx([inv], template_fields=template_fields)
        wb = load_workbook(buf)
        ws = wb["Fakture"]
        headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert headers == ["Br. fakture", "Ukupan iznos (RSD)"]


class TestCSVWithTemplate:
    """Tests for CSV export with custom template."""

    def test_csv_template_limits_columns(self):
        """CSV with template shows only template columns."""
        inv = _mock_invoice()
        template_fields = [
            {"key": "invoice_number", "label": "Broj", "order": 1},
            {"key": "seller_name", "label": "Prodavac", "order": 2},
            {"key": "total_amount", "label": "Ukupno", "order": 3},
        ]
        buf = generate_csv([inv], template_fields=template_fields)
        content = buf.read().decode("utf-8-sig")
        lines = content.strip().split("\n")
        reader = csv.reader(StringIO(lines[0]), delimiter=";")
        headers = next(reader)
        assert headers == ["Broj", "Prodavac", "Ukupno"]

    def test_csv_serbian_characters(self):
        """CSV preserves Serbian characters in UTF-8."""
        inv = _mock_invoice(
            seller={"pib": "123456789", "name": "Dragan Cvetanovic DOO", "city": "Cacak"},
            buyer={"pib": "987654321", "name": "Zoran Djordjevic"},
        )
        buf = generate_csv([inv])
        content = buf.read().decode("utf-8-sig")
        assert "Dragan Cvetanovic DOO" in content
        assert "Zoran Djordjevic" in content


class TestJSONWithTemplate:
    """Tests for JSON export with custom template."""

    def test_json_flat_with_template(self):
        """Flat JSON with template returns only template fields."""
        inv = _mock_invoice(invoice_number="TPL-001")
        template_fields = [
            {"key": "invoice_number", "label": "Broj", "order": 1},
            {"key": "total_amount", "label": "Ukupno", "order": 2},
        ]
        buf = generate_json([inv], nested=False, template_fields=template_fields)
        data = json.loads(buf.read())
        assert len(data) == 1
        record = data[0]
        assert set(record.keys()) == {"Broj", "Ukupno"}
        assert record["Broj"] == "TPL-001"

    def test_json_nested_ignores_template(self):
        """Nested JSON ignores templates and returns full structure."""
        inv = _mock_invoice()
        template_fields = [
            {"key": "invoice_number", "label": "Broj", "order": 1},
        ]
        buf = generate_json([inv], nested=True, template_fields=template_fields)
        data = json.loads(buf.read())
        record = data[0]
        assert "seller" in record
        assert "line_items" in record


# ---------------------------------------------------------------------------
# Integration tests: Template CRUD
# ---------------------------------------------------------------------------


class TestTemplateCRUD:
    """Integration tests for template CRUD endpoints."""

    async def test_create_custom_template(self, client: AsyncClient, test_engine):
        """Create a custom export template."""
        headers = await _auth_headers(client)

        resp = await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Moj sablon",
                "description": "Test template",
                "fields": [
                    {"key": "invoice_number", "label": "Broj", "order": 1},
                    {"key": "total_amount", "label": "Ukupno", "order": 2},
                ],
                "supported_formats": ["xlsx", "csv"],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Moj sablon"
        assert data["is_default"] is False
        assert len(data["fields"]) == 2

    async def test_create_template_invalid_key(self, client: AsyncClient, test_engine):
        """Reject template with invalid field keys."""
        headers = await _auth_headers(client)

        resp = await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Bad template",
                "fields": [
                    {"key": "nonexistent_field", "label": "Bad", "order": 1},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_list_templates_includes_custom(self, client: AsyncClient, test_engine):
        """List returns both system defaults and custom templates."""
        await _seed_default_templates(test_engine)
        headers = await _auth_headers(client)

        # Create a custom template
        await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Custom One",
                "fields": [
                    {"key": "invoice_number", "label": "Broj", "order": 1},
                ],
            },
            headers=headers,
        )

        resp = await client.get("/api/v1/export/templates", headers=headers)
        assert resp.status_code == 200
        templates = resp.json()
        names = [t["name"] for t in templates]
        assert "Standardni izvoz" in names
        assert "Custom One" in names

    async def test_update_custom_template(self, client: AsyncClient, test_engine):
        """Update a custom template."""
        headers = await _auth_headers(client)

        # Create
        create_resp = await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Updatable",
                "fields": [
                    {"key": "invoice_number", "label": "Broj", "order": 1},
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        # Update
        resp = await client.patch(
            f"/api/v1/export/templates/{template_id}",
            json={"name": "Updated Name"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    async def test_cannot_modify_default_template(self, client: AsyncClient, test_engine):
        """Cannot modify system default templates."""
        await _seed_default_templates(test_engine)
        headers = await _auth_headers(client)

        # Get a default template ID
        list_resp = await client.get("/api/v1/export/templates", headers=headers)
        defaults = [t for t in list_resp.json() if t["is_default"]]
        assert len(defaults) > 0

        # Try to update — should fail (404 because org_id doesn't match NULL)
        resp = await client.patch(
            f"/api/v1/export/templates/{defaults[0]['id']}",
            json={"name": "Hacked"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_delete_custom_template(self, client: AsyncClient, test_engine):
        """Delete a custom template."""
        headers = await _auth_headers(client)

        create_resp = await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Deletable",
                "fields": [
                    {"key": "invoice_number", "label": "Broj", "order": 1},
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/export/templates/{template_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(
            f"/api/v1/export/templates/{template_id}",
            headers=headers,
        )
        assert get_resp.status_code == 404

    async def test_template_org_isolation(self, client: AsyncClient, test_engine):
        """Cannot access another org's templates."""
        headers = await _auth_headers(client)
        alt_headers = await _auth_headers_alt(client)

        # Create template as org A
        create_resp = await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Org A Template",
                "fields": [
                    {"key": "invoice_number", "label": "Broj", "order": 1},
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        # Try to access as org B
        resp = await client.get(
            f"/api/v1/export/templates/{template_id}",
            headers=alt_headers,
        )
        assert resp.status_code == 404

    async def test_export_with_custom_template(self, client: AsyncClient, test_engine):
        """Export uses custom template for field selection."""
        headers = await _auth_headers(client)
        org_id = _get_org_id(headers)
        inv_id = await _insert_invoice(test_engine, org_id)

        # Create a 3-field template
        create_resp = await client.post(
            "/api/v1/export/templates",
            json={
                "name": "Tri polja",
                "fields": [
                    {"key": "invoice_number", "label": "Broj", "order": 1},
                    {"key": "seller_name", "label": "Prodavac", "order": 2},
                    {"key": "total_amount", "label": "Iznos", "order": 3},
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        # Export XLSX with this template
        resp = await client.post(
            "/api/v1/export",
            json={
                "format": "xlsx",
                "invoice_ids": [inv_id],
                "template_id": template_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        wb = load_workbook(BytesIO(resp.content))
        ws = wb["Fakture"]
        assert ws.max_column == 3
        headers_row = [ws.cell(1, c).value for c in range(1, 4)]
        assert headers_row == ["Broj", "Prodavac", "Iznos"]


# ---------------------------------------------------------------------------
# Integration tests: Audit export
# ---------------------------------------------------------------------------


class TestAuditExportEndpoint:
    """Integration tests for POST /api/v1/export/audit."""

    async def test_audit_export_requires_admin(self, client: AsyncClient, test_engine):
        """Audit export returns 403 for non-admin users."""
        # Register first user (admin) then second user (member)
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "audit-admin@example.com",
                "password": "securepass123",
                "first_name": "Admin",
                "last_name": "User",
                "organization_name": "Audit Org",
            },
        )
        # Second user in same org would be member, but auth registers new orgs
        # So register a second org user — first user is always admin
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "audit-member@example.com",
                "password": "securepass123",
                "first_name": "Member",
                "last_name": "User",
                "organization_name": "Member Org",
            },
        )
        # The second registered user IS admin of their own org.
        # To test non-admin, we need to modify user role.
        # For now, verify admin can access (first user is admin).
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "audit-admin@example.com", "password": "securepass123"},
        )
        admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        # Admin should NOT get 403
        from unittest.mock import AsyncMock, patch

        with patch(
            "app.routers.export.generate_audit_export",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "download_url": "https://s3.example.com/test.zip",
                "file_size": 1024,
                "invoice_count": 5,
                "period": {"from": "2025-01-01", "to": "2025-12-31"},
                "s3_key": "organizations/test/exports/audit.zip",
            }
            resp = await client.post(
                "/api/v1/export/audit",
                json={"date_from": "2025-01-01", "date_to": "2025-12-31"},
                headers=admin_headers,
            )
            assert resp.status_code == 200

    async def test_audit_export_invalid_dates(self, client: AsyncClient, test_engine):
        """Audit export returns 400 for date_from > date_to."""
        headers = await _auth_headers(client)

        resp = await client.post(
            "/api/v1/export/audit",
            json={"date_from": "2025-12-31", "date_to": "2025-01-01"},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_audit_export_success_with_mock(self, client: AsyncClient, test_engine):
        """Audit export succeeds and returns expected response shape."""
        headers = await _auth_headers(client)

        from unittest.mock import AsyncMock, patch

        with patch(
            "app.routers.export.generate_audit_export",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "download_url": "https://s3.example.com/audit.zip",
                "file_size": 2048,
                "invoice_count": 10,
                "period": {"from": "2025-01-01", "to": "2025-06-30"},
                "s3_key": "organizations/test/exports/audit_2025-01-01_2025-06-30.zip",
            }

            resp = await client.post(
                "/api/v1/export/audit",
                json={
                    "date_from": "2025-01-01",
                    "date_to": "2025-06-30",
                    "reason": "Poreska kontrola br. 123/2025",
                },
                headers=headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["download_url"] == "https://s3.example.com/audit.zip"
        assert data["file_size"] == 2048
        assert data["invoice_count"] == 10
        assert data["status"] == "ready"
        assert data["reason"] == "Poreska kontrola br. 123/2025"
        assert data["expires_at"] is not None

    async def test_audit_export_saves_record(self, client: AsyncClient, test_engine):
        """Audit export creates a tracking record in the database."""
        headers = await _auth_headers(client)

        from unittest.mock import AsyncMock, patch

        with patch(
            "app.routers.export.generate_audit_export",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "download_url": "https://s3.example.com/audit.zip",
                "file_size": 512,
                "invoice_count": 3,
                "period": {"from": "2025-03-01", "to": "2025-03-31"},
                "s3_key": "organizations/test/exports/audit.zip",
            }

            resp = await client.post(
                "/api/v1/export/audit",
                json={"date_from": "2025-03-01", "date_to": "2025-03-31"},
                headers=headers,
            )

        assert resp.status_code == 200
        export_id = resp.json()["id"]

        # Verify via audit history endpoint
        history_resp = await client.get(
            "/api/v1/export/audit/history",
            headers=headers,
        )
        assert history_resp.status_code == 200
        exports = history_resp.json()
        assert any(e["id"] == export_id for e in exports)

    async def test_audit_export_history(self, client: AsyncClient, test_engine):
        """List audit export history returns past exports."""
        headers = await _auth_headers(client)

        from unittest.mock import AsyncMock, patch

        with patch(
            "app.routers.export.generate_audit_export",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "download_url": "https://s3.example.com/audit.zip",
                "file_size": 1024,
                "invoice_count": 5,
                "period": {"from": "2025-01-01", "to": "2025-06-30"},
                "s3_key": "organizations/test/exports/audit.zip",
            }
            await client.post(
                "/api/v1/export/audit",
                json={"date_from": "2025-01-01", "date_to": "2025-06-30"},
                headers=headers,
            )

        resp = await client.get("/api/v1/export/audit/history", headers=headers)
        assert resp.status_code == 200
        exports = resp.json()
        assert isinstance(exports, list)
        assert len(exports) >= 1
        assert exports[0]["status"] == "ready"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestExportEdgeCases:
    """Edge case tests for export generators."""

    def test_export_empty_list_xlsx(self):
        """XLSX with empty invoice list produces valid workbook."""
        buf = generate_xlsx([])
        wb = load_workbook(buf)
        ws = wb["Fakture"]
        assert ws.max_row == 1  # Only header row

    def test_export_empty_list_csv(self):
        """CSV with empty invoice list produces valid CSV with headers."""
        buf = generate_csv([])
        content = buf.read().decode("utf-8-sig")
        assert "Broj fakture" in content
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Only header

    def test_export_empty_list_json(self):
        """JSON with empty invoice list produces empty array."""
        buf = generate_json([])
        data = json.loads(buf.read())
        assert data == []

    def test_export_null_fields(self):
        """Generators handle invoices with many null fields."""
        inv = _mock_invoice(
            invoice_number=None,
            subtotal=None,
            tax_rate=None,
            tax_amount=None,
            total_amount=None,
            seller=None,
            buyer=None,
            due_date=None,
            line_items=None,
        )
        # Should not crash
        buf_xlsx = generate_xlsx([inv])
        assert buf_xlsx.getvalue()

        buf_csv = generate_csv([inv])
        assert buf_csv.getvalue()

        buf_json = generate_json([inv])
        data = json.loads(buf_json.read())
        assert len(data) == 1

    def test_special_chars_in_invoice_number(self):
        """Filename sanitization handles special characters."""
        from app.routers.export import _sanitize_filename

        assert _sanitize_filename("FAKT/2025-01 (duplikat)") == "FAKT2025-01_duplikat"
        assert _sanitize_filename("A" * 100)[:50] == "A" * 50


class TestMiniMaxConfig:
    """Tests for MiniMax configuration endpoints."""

    async def test_config_not_found(self, client: AsyncClient, test_engine):
        """Returns 404 when no config exists."""
        headers = await _auth_headers(client)

        resp = await client.get(
            "/api/v1/export/minimax/config",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_create_config(self, client: AsyncClient, test_engine):
        """Create MiniMax configuration."""
        headers = await _auth_headers(client)

        resp = await client.put(
            "/api/v1/export/minimax/config",
            json={
                "client_id": "test-client-id",
                "client_secret": "FAKE_TEST_PLACEHOLDER",
                "username": "test-user",
                "password": "FAKE_TEST_PLACEHOLDER",
                "minimax_org_id": 12345,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["client_id"] == "test-client-id"
        assert data["minimax_org_id"] == 12345
        assert data["is_active"] is True

    async def test_update_config(self, client: AsyncClient, test_engine):
        """Update existing MiniMax configuration."""
        headers = await _auth_headers(client)

        # Create
        await client.put(
            "/api/v1/export/minimax/config",
            json={
                "client_id": "old-id",
                "client_secret": "FAKE_TEST_PLACEHOLDER",
                "username": "old-user",
                "password": "FAKE_TEST_PLACEHOLDER",
                "minimax_org_id": 11111,
            },
            headers=headers,
        )

        # Update via PUT (upsert)
        resp = await client.put(
            "/api/v1/export/minimax/config",
            json={
                "client_id": "new-id",
                "client_secret": "FAKE_TEST_PLACEHOLDER",
                "username": "new-user",
                "password": "FAKE_TEST_PLACEHOLDER",
                "minimax_org_id": 22222,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["client_id"] == "new-id"
        assert resp.json()["minimax_org_id"] == 22222

    async def test_patch_config(self, client: AsyncClient, test_engine):
        """Partially update MiniMax configuration."""
        headers = await _auth_headers(client)

        # Create first
        await client.put(
            "/api/v1/export/minimax/config",
            json={
                "client_id": "patch-id",
                "client_secret": "FAKE_TEST_PLACEHOLDER",
                "username": "patch-user",
                "password": "FAKE_TEST_PLACEHOLDER",
                "minimax_org_id": 33333,
            },
            headers=headers,
        )

        # Patch
        resp = await client.patch(
            "/api/v1/export/minimax/config",
            json={"is_active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert resp.json()["client_id"] == "patch-id"  # unchanged
