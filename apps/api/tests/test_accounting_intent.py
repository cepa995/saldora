"""
Tests for the AccountingIntent generation pipeline (Issue #34).

Unit tests for each pipeline step (classify_document, detect_transaction_type,
determine_vat_treatment, suggest_konta, build_vat_breakdown) and integration
tests for the verify endpoint and GET accounting-intent endpoint.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token
from app.models.invoice import Invoice
from app.services.accounting_intent import (
    build_vat_breakdown,
    classify_document,
    detect_transaction_type,
    determine_vat_treatment,
    generate_pdv_book_entries,
    suggest_konta,
)

# ---- Helpers ----

ORG_PIB = "100000016"  # Valid Serbian PIB


async def _register_and_login(
    client: AsyncClient,
    email: str = "acct-test@example.com",
    password: str = "securepass123",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Acct",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": "Acct Test Org"},
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
            invoice_number=overrides.get("invoice_number", "AI-001"),
            invoice_date=overrides.get("invoice_date", date(2026, 3, 1)),
            seller=overrides.get("seller", {"name": "Dobavljač DOO", "pib": "123456789"}),
            buyer=overrides.get("buyer", {"name": "Kupac DOO", "pib": ORG_PIB}),
            subtotal=overrides.get("subtotal", Decimal("10000.00")),
            tax_rate=overrides.get("tax_rate", Decimal("20.00")),
            tax_amount=overrides.get("tax_amount", Decimal("2000.00")),
            total_amount=overrides.get("total_amount", Decimal("12000.00")),
            currency=overrides.get("currency", "RSD"),
            line_items=overrides.get("line_items"),
            tax_groups=overrides.get("tax_groups"),
            raw_ocr_text=overrides.get("raw_ocr_text"),
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
    inv.invoice_number = kwargs.get("invoice_number", "AI-001")
    inv.invoice_date = kwargs.get("invoice_date", date(2026, 3, 1))
    inv.seller = kwargs.get("seller", {"name": "Dobavljač", "pib": "123456789"})
    inv.buyer = kwargs.get("buyer", {"name": "Kupac", "pib": ORG_PIB})
    inv.subtotal = kwargs.get("subtotal", Decimal("10000.00"))
    inv.tax_rate = kwargs.get("tax_rate", Decimal("20.00"))
    inv.tax_amount = kwargs.get("tax_amount", Decimal("2000.00"))
    inv.total_amount = kwargs.get("total_amount", Decimal("12000.00"))
    inv.currency = kwargs.get("currency", "RSD")
    inv.line_items = kwargs.get("line_items")
    inv.tax_groups = kwargs.get("tax_groups")
    inv.raw_ocr_text = kwargs.get("raw_ocr_text")
    return inv


# ---- Step 1: Document Classification ----


class TestClassifyDocument:
    """Tests for classify_document()."""

    def test_input_invoice_buyer_matches_org(self):
        """Buyer PIB matching org PIB → INPUT_INVOICE."""
        inv = _make_invoice(
            seller={"name": "Seller", "pib": "123456789"},
            buyer={"name": "Us", "pib": ORG_PIB},
        )
        doc_type, confidence = classify_document(inv, ORG_PIB)
        assert doc_type == "INPUT_INVOICE"
        assert confidence == Decimal("0.95")

    def test_output_invoice_seller_matches_org(self):
        """Seller PIB matching org PIB → OUTPUT_INVOICE."""
        inv = _make_invoice(
            seller={"name": "Us", "pib": ORG_PIB},
            buyer={"name": "Customer", "pib": "987654321"},
        )
        doc_type, confidence = classify_document(inv, ORG_PIB)
        assert doc_type == "OUTPUT_INVOICE"
        assert confidence == Decimal("0.95")

    def test_no_org_pib_defaults_input(self):
        """No org PIB → default INPUT_INVOICE with lower confidence."""
        inv = _make_invoice()
        doc_type, confidence = classify_document(inv, None)
        assert doc_type == "INPUT_INVOICE"
        assert confidence == Decimal("0.60")

    def test_credit_note_detected(self):
        """Credit note keywords → CREDIT_NOTE_IN."""
        inv = _make_invoice(
            buyer={"name": "Us", "pib": ORG_PIB},
            raw_ocr_text="Knjižno odobrenje br. 123",
        )
        doc_type, _ = classify_document(inv, ORG_PIB)
        assert doc_type == "CREDIT_NOTE_IN"

    def test_credit_note_output(self):
        """Credit note on output invoice → CREDIT_NOTE_OUT."""
        inv = _make_invoice(
            seller={"name": "Us", "pib": ORG_PIB},
            buyer={"name": "Customer", "pib": "987654321"},
            raw_ocr_text="Storno fakture",
        )
        doc_type, _ = classify_document(inv, ORG_PIB)
        assert doc_type == "CREDIT_NOTE_OUT"

    def test_debit_note_detected(self):
        """Debit note keywords → DEBIT_NOTE_IN."""
        inv = _make_invoice(
            buyer={"name": "Us", "pib": ORG_PIB},
            raw_ocr_text="Knjižno zaduženje br. 456",
        )
        doc_type, _ = classify_document(inv, ORG_PIB)
        assert doc_type == "DEBIT_NOTE_IN"

    def test_advance_invoice_detected(self):
        """Advance keywords → ADVANCE_INVOICE."""
        inv = _make_invoice(raw_ocr_text="Avansna faktura za ugovor")
        doc_type, _ = classify_document(inv, None)
        assert doc_type == "ADVANCE_INVOICE"

    def test_proforma_detected(self):
        """Proforma keywords → PROFORMA."""
        inv = _make_invoice(raw_ocr_text="Profaktura br. 789")
        doc_type, _ = classify_document(inv, None)
        assert doc_type == "PROFORMA"


# ---- Step 2: Transaction Type ----


class TestDetectTransactionType:
    """Tests for detect_transaction_type()."""

    def test_domestic_serbian_pib(self):
        """Serbian 9-digit PIB → DOMESTIC."""
        inv = _make_invoice(seller={"name": "Serbian Co", "pib": "123456789"})
        txn_type, confidence = detect_transaction_type(inv, "INPUT_INVOICE")
        assert txn_type == "DOMESTIC"
        assert confidence == Decimal("0.95")

    def test_foreign_eu_vat_id(self):
        """EU VAT ID prefix → FOREIGN_EU."""
        inv = _make_invoice(seller={"name": "German Co", "pib": "DE123456789"})
        txn_type, confidence = detect_transaction_type(inv, "INPUT_INVOICE")
        assert txn_type == "FOREIGN_EU"
        assert confidence == Decimal("0.90")

    def test_foreign_non_eu(self):
        """Non-EU, non-Serbian tax ID → FOREIGN_NON_EU."""
        inv = _make_invoice(seller={"name": "US Co", "pib": "US12-3456789"})
        txn_type, _ = detect_transaction_type(inv, "INPUT_INVOICE")
        assert txn_type == "FOREIGN_NON_EU"

    def test_reverse_charge_keyword(self):
        """'obrnuta naplata' in OCR → REVERSE_CHARGE."""
        inv = _make_invoice(
            raw_ocr_text="Primena mehanizma obrnuta naplata PDV",
        )
        txn_type, _ = detect_transaction_type(inv, "INPUT_INVOICE")
        assert txn_type == "REVERSE_CHARGE"

    def test_internal_same_seller_buyer(self):
        """Same seller and buyer PIB → INTERNAL."""
        inv = _make_invoice(
            seller={"name": "Company", "pib": "100000016"},
            buyer={"name": "Company Branch", "pib": "100000016"},
        )
        txn_type, confidence = detect_transaction_type(inv, "INPUT_INVOICE")
        assert txn_type == "INTERNAL"
        assert confidence == Decimal("0.95")

    def test_no_counterparty_pib(self):
        """Missing counterparty PIB → DOMESTIC with low confidence."""
        inv = _make_invoice(seller={"name": "Unknown Corp"})
        txn_type, confidence = detect_transaction_type(inv, "INPUT_INVOICE")
        assert txn_type == "DOMESTIC"
        assert confidence == Decimal("0.60")

    def test_output_checks_buyer(self):
        """Output invoice checks buyer PIB for transaction type."""
        inv = _make_invoice(
            seller={"name": "Us", "pib": ORG_PIB},
            buyer={"name": "German Client", "pib": "DE987654321"},
        )
        txn_type, _ = detect_transaction_type(inv, "OUTPUT_INVOICE")
        assert txn_type == "FOREIGN_EU"


# ---- Step 3: VAT Treatment ----


class TestDetermineVatTreatment:
    """Tests for determine_vat_treatment()."""

    def test_output_standard_20(self):
        """Output invoice with 20% tax rate → OUTPUT_STANDARD."""
        inv = _make_invoice(tax_rate=Decimal("20.00"))
        vat, deductible, _ = determine_vat_treatment(inv, "OUTPUT_INVOICE", "DOMESTIC")
        assert vat == "OUTPUT_STANDARD"
        assert deductible is True

    def test_output_reduced_10(self):
        """Output invoice with 10% tax rate → OUTPUT_REDUCED."""
        inv = _make_invoice(tax_rate=Decimal("10.00"))
        vat, _, _ = determine_vat_treatment(inv, "OUTPUT_INVOICE", "DOMESTIC")
        assert vat == "OUTPUT_REDUCED"

    def test_output_exempt_zero(self):
        """Output invoice with 0% tax rate → OUTPUT_EXEMPT."""
        inv = _make_invoice(tax_rate=Decimal("0"))
        vat, _, _ = determine_vat_treatment(inv, "OUTPUT_INVOICE", "DOMESTIC")
        assert vat == "OUTPUT_EXEMPT"

    def test_input_deductible_full(self):
        """Regular input invoice → DEDUCTIBLE_FULL."""
        inv = _make_invoice(
            line_items=[{"description": "Konsultantske usluge", "total": "10000"}],
        )
        vat, deductible, _ = determine_vat_treatment(inv, "INPUT_INVOICE", "DOMESTIC")
        assert vat == "DEDUCTIBLE_FULL"
        assert deductible is True

    def test_input_reprezentacija_partial(self):
        """Invoice with 'ručak' keyword → DEDUCTIBLE_PARTIAL (50%)."""
        inv = _make_invoice(
            line_items=[{"description": "Poslovni ručak za klijente", "total": "5000"}],
        )
        vat, deductible, _ = determine_vat_treatment(inv, "INPUT_INVOICE", "DOMESTIC")
        assert vat == "DEDUCTIBLE_PARTIAL"
        assert deductible is True

    def test_input_gorivo_non_deductible(self):
        """Invoice with fuel keywords → NON_DEDUCTIBLE."""
        inv = _make_invoice(
            line_items=[{"description": "Dizel gorivo 50L", "total": "8000"}],
        )
        vat, deductible, _ = determine_vat_treatment(inv, "INPUT_INVOICE", "DOMESTIC")
        assert vat == "NON_DEDUCTIBLE"
        assert deductible is False

    def test_input_donacija_non_deductible(self):
        """Invoice with donation keyword → NON_DEDUCTIBLE."""
        inv = _make_invoice(raw_ocr_text="Donacija za humanitarnu akciju")
        vat, deductible, _ = determine_vat_treatment(inv, "INPUT_INVOICE", "DOMESTIC")
        assert vat == "NON_DEDUCTIBLE"
        assert deductible is False

    def test_reverse_charge_input(self):
        """Reverse charge on input → REVERSE_CHARGE_IN."""
        inv = _make_invoice()
        vat, _, _ = determine_vat_treatment(inv, "INPUT_INVOICE", "REVERSE_CHARGE")
        assert vat == "REVERSE_CHARGE_IN"

    def test_reverse_charge_output(self):
        """Reverse charge on output → REVERSE_CHARGE_OUT."""
        inv = _make_invoice()
        vat, _, _ = determine_vat_treatment(inv, "OUTPUT_INVOICE", "REVERSE_CHARGE")
        assert vat == "REVERSE_CHARGE_OUT"


# ---- Step 4: Konta Suggestion ----


class TestSuggestKonta:
    """Tests for suggest_konta()."""

    def test_input_domestic_service(self):
        """Input domestic services invoice → correct debit/credit konta."""
        inv = _make_invoice(
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("2000.00"),
            total_amount=Decimal("12000.00"),
            line_items=[{"description": "IT konsultacije", "total": "10000"}],
        )
        konta, _ = suggest_konta(inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL")
        assert "debit" in konta
        assert "credit" in konta
        # Should have expense + VAT on debit
        debit_kontos = [e["konto"] for e in konta["debit"]]
        assert "5330" in debit_kontos  # services
        assert "2700" in debit_kontos  # input VAT
        # Domestic payable on credit
        credit_kontos = [e["konto"] for e in konta["credit"]]
        assert "4330" in credit_kontos

    def test_input_foreign_payable(self):
        """Input foreign invoice → foreign payable konto 4340."""
        inv = _make_invoice(
            subtotal=Decimal("5000.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("5000.00"),
        )
        konta, _ = suggest_konta(inv, "INPUT_INVOICE", "FOREIGN_EU", "DEDUCTIBLE_FULL")
        credit_kontos = [e["konto"] for e in konta["credit"]]
        assert "4340" in credit_kontos

    def test_input_partial_deductible(self):
        """Partially deductible → split VAT between 2700 and 5799."""
        inv = _make_invoice(
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("2000.00"),
            total_amount=Decimal("12000.00"),
            line_items=[{"description": "Poslovni ručak", "total": "10000"}],
        )
        konta, _ = suggest_konta(inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_PARTIAL")
        debit_kontos = [e["konto"] for e in konta["debit"]]
        assert "2700" in debit_kontos  # deductible portion
        assert "5799" in debit_kontos  # non-deductible portion

    def test_output_invoice_konta(self):
        """Output invoice → receivable, revenue, and output VAT."""
        inv = _make_invoice(
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("2000.00"),
            total_amount=Decimal("12000.00"),
        )
        konta, _ = suggest_konta(inv, "OUTPUT_INVOICE", "DOMESTIC", "OUTPUT_STANDARD")
        debit_kontos = [e["konto"] for e in konta["debit"]]
        credit_kontos = [e["konto"] for e in konta["credit"]]
        assert "2040" in debit_kontos  # receivable
        assert "6010" in credit_kontos  # revenue
        assert "4700" in credit_kontos  # output VAT


# ---- VAT Breakdown Helper ----


class TestBuildVatBreakdown:
    """Tests for build_vat_breakdown()."""

    def test_single_rate(self):
        """Single tax rate → one entry in breakdown."""
        inv = _make_invoice(
            subtotal=Decimal("10000.00"),
            tax_rate=Decimal("20.00"),
            tax_amount=Decimal("2000.00"),
        )
        breakdown = build_vat_breakdown(inv)
        assert "rate_20.00" in breakdown
        assert breakdown["rate_20.00"]["base"] == "10000.00"
        assert breakdown["rate_20.00"]["tax"] == "2000.00"

    def test_tax_groups_multi_rate(self):
        """Multiple tax groups → multiple entries."""
        inv = _make_invoice(
            tax_groups=[
                {"rate": "20.00", "base_amount": "8000.00", "tax_amount": "1600.00"},
                {"rate": "10.00", "base_amount": "2000.00", "tax_amount": "200.00"},
            ],
        )
        breakdown = build_vat_breakdown(inv)
        assert "rate_20.00" in breakdown
        assert "rate_10.00" in breakdown
        assert breakdown["rate_20.00"]["base"] == "8000.00"
        assert breakdown["rate_10.00"]["tax"] == "200.00"

    def test_no_tax(self):
        """No tax fields → rate_0 entry."""
        inv = _make_invoice(
            subtotal=Decimal("0"),
            tax_rate=None,
            tax_amount=Decimal("0"),
        )
        breakdown = build_vat_breakdown(inv)
        assert len(breakdown) == 1


# ---- Integration Tests ----


async def test_verify_creates_accounting_intent(client: AsyncClient, test_engine):
    """Verifying an invoice creates an AccountingIntent."""
    headers = await _register_and_login(client, email="ai-create@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    # Verify the invoice
    resp = await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    assert resp.status_code == 200

    # GET the accounting intent
    resp = await client.get(f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["invoice_id"] == invoice_id
    assert data["document_type"] in (
        "INPUT_INVOICE",
        "OUTPUT_INVOICE",
        "CREDIT_NOTE_IN",
        "CREDIT_NOTE_OUT",
        "ADVANCE_INVOICE",
        "PROFORMA",
    )
    assert data["transaction_type"] in (
        "DOMESTIC",
        "FOREIGN_EU",
        "FOREIGN_NON_EU",
        "REVERSE_CHARGE",
        "EXEMPT",
        "INTERNAL",
    )
    assert "vat_breakdown" in data
    assert "suggested_konta" in data
    assert "confidence" in data


async def test_get_accounting_intent_404_before_verify(client: AsyncClient, test_engine):
    """GET accounting intent returns 404 for unverified invoice."""
    headers = await _register_and_login(client, email="ai-404@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    resp = await client.get(f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers)
    assert resp.status_code == 404


async def test_accounting_intent_domestic_input(client: AsyncClient, test_engine):
    """Domestic input invoice gets correct classification."""
    headers = await _register_and_login(client, email="ai-domestic@example.com")
    org_id = _get_org_id(headers)

    invoice_id = await _insert_invoice(
        test_engine,
        org_id,
        seller={"name": "Dobavljač DOO", "pib": "123456789"},
        buyer={"name": "Mi DOO", "pib": ORG_PIB},
        subtotal=Decimal("10000.00"),
        tax_rate=Decimal("20.00"),
        tax_amount=Decimal("2000.00"),
        total_amount=Decimal("12000.00"),
    )

    await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)

    resp = await client.get(f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers)
    data = resp.json()

    # Without org PIB set, classification defaults
    assert data["transaction_type"] == "DOMESTIC"
    assert "suggested_konta" in data
    assert "debit" in data["suggested_konta"]
    assert "credit" in data["suggested_konta"]


async def test_reverify_replaces_intent(client: AsyncClient, test_engine):
    """Re-verifying replaces old AccountingIntent with new one."""
    headers = await _register_and_login(client, email="ai-reverify@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    # First verify
    await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    resp1 = await client.get(f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers)
    intent_id_1 = resp1.json()["id"]

    # Reset invoice to review for re-verify
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        from sqlalchemy import text

        await session.execute(
            text("UPDATE invoices SET status = 'review' WHERE id = :id"),
            {"id": invoice_id},
        )
        await session.commit()

    # Re-verify
    await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    resp2 = await client.get(f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers)
    intent_id_2 = resp2.json()["id"]

    # Should be a different intent (old deleted, new created)
    assert intent_id_1 != intent_id_2


# ==== PDV Book Mapping Tests (Issue #35) ====


def _make_invoice(**overrides) -> Invoice:
    """Create a minimal Invoice instance for PDV book mapping tests."""
    defaults = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "status": "verified",
        "invoice_number": "TEST-001",
        "invoice_date": date(2026, 3, 1),
        "seller": {"name": "Prodavac DOO", "pib": "123456789"},
        "buyer": {"name": "Kupac DOO", "pib": ORG_PIB},
        "subtotal": Decimal("10000.00"),
        "tax_rate": Decimal("20"),
        "tax_amount": Decimal("2000.00"),
        "total_amount": Decimal("12000.00"),
        "currency": "RSD",
    }
    defaults.update(overrides)
    return Invoice(**defaults)


class TestPdvBookEntries:
    """Tests for generate_pdv_book_entries()."""

    def test_kpr_input_invoice_20_percent(self):
        """Input invoice at 20% → KPR with polje_8_1, polje_8_2."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL", vat_breakdown, 1
        )

        assert result["book_type"] == "KPR"
        assert result["period"] == "2026-03"
        assert result["sequence"] == 1
        assert result["counterparty_pib"] == "123456789"
        assert result["counterparty_name"] == "Prodavac DOO"
        assert result["base_20"] == "10000"
        assert result["vat_20"] == "2000"
        assert result["pp_pdv_fields"]["polje_8_1"] == "10000"
        assert result["pp_pdv_fields"]["polje_8_2"] == "2000"

    def test_kpr_input_invoice_10_percent(self):
        """Input invoice at 10% → KPR with polje_9_1, polje_9_2."""
        inv = _make_invoice(
            subtotal=Decimal("5000"),
            tax_rate=Decimal("10"),
            tax_amount=Decimal("500"),
            total_amount=Decimal("5500"),
        )
        vat_breakdown = {"rate_10": {"base": "5000", "tax": "500"}}

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL", vat_breakdown, 3
        )

        assert result["book_type"] == "KPR"
        assert result["sequence"] == 3
        assert result["base_10"] == "5000"
        assert result["vat_10"] == "500"
        assert result["pp_pdv_fields"]["polje_9_1"] == "5000"
        assert result["pp_pdv_fields"]["polje_9_2"] == "500"
        assert "polje_8_1" not in result["pp_pdv_fields"]

    def test_kir_output_invoice_20_percent(self):
        """Output invoice at 20% → KIR with polje_3_1, polje_3_2."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "OUTPUT_INVOICE", "DOMESTIC", "OUTPUT_STANDARD", vat_breakdown, 5
        )

        assert result["book_type"] == "KIR"
        assert result["counterparty_pib"] == ORG_PIB
        assert result["counterparty_name"] == "Kupac DOO"
        assert result["pp_pdv_fields"]["polje_3_1"] == "10000"
        assert result["pp_pdv_fields"]["polje_3_2"] == "2000"

    def test_kir_output_invoice_10_percent(self):
        """Output invoice at 10% → KIR with polje_4_1, polje_4_2."""
        inv = _make_invoice()
        vat_breakdown = {"rate_10": {"base": "8000", "tax": "800"}}

        result = generate_pdv_book_entries(
            inv, "OUTPUT_INVOICE", "DOMESTIC", "OUTPUT_REDUCED", vat_breakdown, 1
        )

        assert result["book_type"] == "KIR"
        assert result["pp_pdv_fields"]["polje_4_1"] == "8000"
        assert result["pp_pdv_fields"]["polje_4_2"] == "800"

    def test_multi_rate_invoice(self):
        """Invoice with 20% and 10% items → both polje sets populated."""
        inv = _make_invoice(total_amount=Decimal("16500"))
        vat_breakdown = {
            "rate_20": {"base": "10000", "tax": "2000"},
            "rate_10": {"base": "4000", "tax": "400"},
        }

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL", vat_breakdown, 1
        )

        assert result["base_20"] == "10000"
        assert result["vat_20"] == "2000"
        assert result["base_10"] == "4000"
        assert result["vat_10"] == "400"
        assert result["pp_pdv_fields"]["polje_8_1"] == "10000"
        assert result["pp_pdv_fields"]["polje_8_2"] == "2000"
        assert result["pp_pdv_fields"]["polje_9_1"] == "4000"
        assert result["pp_pdv_fields"]["polje_9_2"] == "400"

    def test_exempt_output(self):
        """Exempt output → polje_6 with base only."""
        inv = _make_invoice(tax_amount=Decimal("0"), total_amount=Decimal("10000"))
        vat_breakdown = {"rate_0": {"base": "10000", "tax": "0"}}

        result = generate_pdv_book_entries(
            inv, "OUTPUT_INVOICE", "DOMESTIC", "OUTPUT_EXEMPT", vat_breakdown, 1
        )

        assert result["book_type"] == "KIR"
        assert result["pp_pdv_fields"]["polje_6"] == "10000"
        assert "polje_3_1" not in result["pp_pdv_fields"]

    def test_reverse_charge_input(self):
        """Reverse charge input → polje_8a fields."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "REVERSE_CHARGE", "REVERSE_CHARGE_IN", vat_breakdown, 1
        )

        assert result["book_type"] == "KPR"
        assert result["pp_pdv_fields"]["polje_8a_1"] == "10000"
        assert result["pp_pdv_fields"]["polje_8a_2"] == "2000"
        assert "polje_8_1" not in result["pp_pdv_fields"]

    def test_reverse_charge_output(self):
        """Reverse charge output → polje_6a fields."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "OUTPUT_INVOICE", "REVERSE_CHARGE", "REVERSE_CHARGE_OUT", vat_breakdown, 1
        )

        assert result["book_type"] == "KIR"
        assert result["pp_pdv_fields"]["polje_6a_1"] == "10000"
        assert result["pp_pdv_fields"]["polje_6a_2"] == "2000"

    def test_partial_deductible(self):
        """Partial deductible → 50% of amounts in polje_8."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_PARTIAL", vat_breakdown, 1
        )

        assert result["pp_pdv_fields"]["polje_8_1"] == "5000.0"
        assert result["pp_pdv_fields"]["polje_8_2"] == "1000.0"

    def test_non_deductible_no_pp_pdv(self):
        """Non-deductible → no pp_pdv_fields entries."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "DOMESTIC", "NON_DEDUCTIBLE", vat_breakdown, 1
        )

        assert result["pp_pdv_fields"] == {}

    def test_credit_note_in_routes_to_kpr(self):
        """Credit note (input) → KPR."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "CREDIT_NOTE_IN", "DOMESTIC", "DEDUCTIBLE_FULL", vat_breakdown, 1
        )

        assert result["book_type"] == "KPR"

    def test_credit_note_out_routes_to_kir(self):
        """Credit note (output) → KIR."""
        inv = _make_invoice()
        vat_breakdown = {"rate_20": {"base": "10000", "tax": "2000"}}

        result = generate_pdv_book_entries(
            inv, "CREDIT_NOTE_OUT", "DOMESTIC", "OUTPUT_STANDARD", vat_breakdown, 1
        )

        assert result["book_type"] == "KIR"

    def test_invoice_number_and_total(self):
        """Entry includes invoice_number and total from invoice."""
        inv = _make_invoice(invoice_number="FAK-2026-042", total_amount=Decimal("60000"))
        vat_breakdown = {"rate_20": {"base": "50000", "tax": "10000"}}

        result = generate_pdv_book_entries(
            inv, "INPUT_INVOICE", "DOMESTIC", "DEDUCTIBLE_FULL", vat_breakdown, 42
        )

        assert result["invoice_number"] == "FAK-2026-042"
        assert result["total"] == "60000"
        assert result["sequence"] == 42


async def test_verify_populates_pdv_book_entries(client: AsyncClient, test_engine):
    """Verify endpoint creates accounting intent with populated pdv_book_entries."""
    headers = await _register_and_login(client, email="pdv-test@example.com")
    org_id = _get_org_id(headers)
    invoice_id = await _insert_invoice(test_engine, org_id)

    await client.post(f"/api/v1/invoices/{invoice_id}/verify", headers=headers)
    resp = await client.get(f"/api/v1/invoices/{invoice_id}/accounting-intent", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    pdv = data["pdv_book_entries"]

    assert pdv["book_type"] in ("KPR", "KIR")
    assert pdv["period"] == "2026-03"
    assert pdv["sequence"] >= 1
    assert "pp_pdv_fields" in pdv
    assert pdv["invoice_number"] == "AI-001"
