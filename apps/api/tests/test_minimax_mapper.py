"""Unit tests for the MiniMax invoice mapper.

Tests cover map_invoice_to_received and _build_invoice_rows. These are pure
mapping functions — no database, Redis, or HTTP calls are needed.

Updated to match the rewritten mapper that uses correct MiniMax RS API
field names (DocumentReference, PaymentType, VATRate as FK, etc.)
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.invoice import Invoice
from app.services.minimax.mapper import (
    CURRENCY_RSD_ID,
    _build_invoice_rows,
    map_invoice_to_received,
    validate_invoice_for_minimax,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_invoice(**kwargs) -> Invoice:
    """Create an in-memory Invoice object for unit testing (no DB required).

    Args:
        **kwargs: Invoice field overrides.

    Returns:
        Invoice instance with sensible defaults.
    """
    inv = Invoice()
    inv.id = uuid4()
    inv.organization_id = uuid4()
    inv.status = kwargs.get("status", "review")
    inv.invoice_number = kwargs.get("invoice_number", "RE-2026-001")
    inv.invoice_date = kwargs.get("invoice_date", date(2026, 3, 1))
    inv.due_date = kwargs.get("due_date", date(2026, 3, 31))
    inv.seller = kwargs.get(
        "seller",
        {"name": "Dobavljač DOO", "pib": "123456789", "postal_code": "11000"},
    )
    inv.buyer = kwargs.get("buyer", {"name": "Kupac DOO", "pib": "987654321"})
    inv.subtotal = kwargs.get("subtotal", Decimal("10000.00"))
    inv.tax_rate = kwargs.get("tax_rate", Decimal("20.00"))
    inv.tax_amount = kwargs.get("tax_amount", Decimal("2000.00"))
    inv.total_amount = kwargs.get("total_amount", Decimal("12000.00"))
    inv.currency = kwargs.get("currency", "RSD")
    inv.line_items = kwargs.get("line_items", None)
    return inv


# ===========================================================================
# A. map_invoice_to_received — core payload structure
# ===========================================================================


def test_map_invoice_document_reference():
    """DocumentReference is set from invoice_number."""
    inv = _make_invoice(invoice_number="INV-001")
    payload = map_invoice_to_received(inv, customer_id=42)
    assert payload["DocumentReference"] == "INV-001"


def test_map_invoice_customer_id():
    """Customer.ID is set from the provided customer_id argument."""
    inv = _make_invoice()
    payload = map_invoice_to_received(inv, customer_id=99)
    assert payload["Customer"]["ID"] == 99


def test_map_invoice_payment_type():
    """PaymentType is always 'N' (unpaid) for received invoices."""
    inv = _make_invoice()
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["PaymentType"] == "N"


def test_map_invoice_dates_present():
    """DateIssued, DateReceived, DateTransaction include time component."""
    inv = _make_invoice(invoice_date=date(2026, 3, 1))
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DateIssued"] == "2026-03-01T00:00:00"
    assert payload["DateReceived"] == "2026-03-01T00:00:00"
    assert payload["DateTransaction"] == "2026-03-01T00:00:00"


def test_map_invoice_due_date():
    """DateDue is set with time component when due_date is present."""
    inv = _make_invoice(due_date=date(2026, 3, 31))
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DateDue"] == "2026-03-31T00:00:00"


def test_map_invoice_no_invoice_date():
    """Date fields are omitted when invoice_date is None."""
    inv = _make_invoice()
    inv.invoice_date = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "DateIssued" not in payload
    assert "DateReceived" not in payload
    assert "DateTransaction" not in payload


def test_map_invoice_no_due_date_defaults_to_plus_30():
    """DateDue defaults to invoice_date + 30 days when due_date is None."""
    inv = _make_invoice(invoice_date=date(2026, 3, 1))
    inv.due_date = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DateDue"] == "2026-03-31T00:00:00"


def test_map_invoice_total_amount():
    """InvoiceAmount and InvoiceAmountDomesticCurrency are set as rounded floats."""
    inv = _make_invoice(total_amount=Decimal("12000.00"))
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["InvoiceAmount"] == pytest.approx(12000.0)
    assert payload["InvoiceAmountDomesticCurrency"] == pytest.approx(12000.0)


def test_map_invoice_no_total_amount():
    """InvoiceAmount is omitted when total_amount is None."""
    inv = _make_invoice()
    inv.total_amount = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "InvoiceAmount" not in payload
    assert "InvoiceAmountDomesticCurrency" not in payload


def test_map_invoice_with_currency_id():
    """Currency.ID is included when currency_id is provided."""
    inv = _make_invoice()
    payload = map_invoice_to_received(inv, customer_id=1, currency_id=5)
    assert payload["Currency"]["ID"] == 5


def test_map_invoice_default_currency_rsd():
    """Currency defaults to RSD (ID=2) when currency_id is None."""
    inv = _make_invoice()
    payload = map_invoice_to_received(inv, customer_id=1, currency_id=None)
    assert payload["Currency"]["ID"] == CURRENCY_RSD_ID


def test_map_invoice_empty_invoice_number():
    """None invoice_number maps to 'N/A' for DocumentReference."""
    inv = _make_invoice()
    inv.invoice_number = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DocumentReference"] == "N/A"


# ===========================================================================
# B. map_invoice_to_received — rows integration
# ===========================================================================


def test_map_invoice_includes_rows_from_line_items():
    """Line items produce ReceivedInvoiceRows in the payload."""
    inv = _make_invoice(
        line_items=[
            {
                "description": "IT usluge",
                "total": "10000.00",
                "unit_price": "10000.00",
                "quantity": 1,
                "tax_rate": "20.00",
            }
        ]
    )
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "ReceivedInvoiceRows" in payload
    assert len(payload["ReceivedInvoiceRows"]) == 1


def test_map_invoice_no_rows_when_no_line_items_and_no_total():
    """ReceivedInvoiceRows is absent when no line items and total_amount is None."""
    inv = _make_invoice()
    inv.line_items = None
    inv.total_amount = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "ReceivedInvoiceRows" not in payload


def test_map_invoice_fallback_row_when_no_line_items():
    """Single fallback row is created from subtotal when line_items is None."""
    inv = _make_invoice(
        invoice_number="RE-001",
        total_amount=Decimal("12000.00"),
        subtotal=Decimal("10000.00"),
        tax_rate=Decimal("20.00"),
    )
    inv.line_items = None
    payload = map_invoice_to_received(inv, customer_id=1)
    rows = payload["ReceivedInvoiceRows"]
    assert len(rows) == 1
    assert rows[0]["Value"] == pytest.approx(10000.0)  # Uses subtotal, not total
    assert rows[0]["VATRate"] == {"ID": 4}  # 20% maps to VatRate ID 4


# ===========================================================================
# C. _build_invoice_rows — line items
# ===========================================================================


def test_build_rows_from_line_items():
    """Line items produce one row dict per item."""
    inv = _make_invoice(
        line_items=[
            {"description": "Konsultantske usluge", "total": "5000.00"},
            {"description": "Softverska licenca", "total": "3000.00"},
        ]
    )
    rows = _build_invoice_rows(inv)
    assert len(rows) == 2


def test_build_rows_description():
    """Row Description is mapped from line item description."""
    inv = _make_invoice(line_items=[{"description": "Gorivo dizel"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Description"] == "Gorivo dizel"


def test_build_rows_value_from_total():
    """Row Value is mapped from line item total as rounded float."""
    inv = _make_invoice(line_items=[{"description": "Test", "total": "8500.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Value"] == pytest.approx(8500.0)
    assert isinstance(rows[0]["Value"], float)


def test_build_rows_value_from_tax_base():
    """Row Value prefers tax_base over total when both present."""
    inv = _make_invoice(
        line_items=[{"description": "Test", "tax_base": "7500.00", "total": "9000.00"}]
    )
    rows = _build_invoice_rows(inv)
    assert rows[0]["Value"] == pytest.approx(7500.0)


def test_build_rows_value_from_qty_price():
    """Row Value calculated from qty * price when no total or tax_base."""
    inv = _make_invoice(line_items=[{"description": "Test", "unit_price": "500.00", "quantity": 3}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Value"] == pytest.approx(1500.0)


def test_build_rows_quantity():
    """Row Quantity is mapped from item quantity as float."""
    inv = _make_invoice(line_items=[{"description": "Test", "quantity": 3}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Quantity"] == pytest.approx(3.0)


def test_build_rows_price():
    """Row Price is mapped from item unit_price."""
    inv = _make_invoice(line_items=[{"description": "Test", "unit_price": "250.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Price"] == pytest.approx(250.0)


def test_build_rows_vat_rate_as_fk():
    """Row VATRate is a FK dict, not a raw number."""
    inv = _make_invoice(line_items=[{"description": "Test", "tax_rate": "20.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["VATRate"] == {"ID": 4}  # 20% maps to VatRate ID 4


def test_build_rows_vat_rate_10_percent():
    """10% tax rate maps to VatRate ID 5."""
    inv = _make_invoice(line_items=[{"description": "Test", "tax_rate": "10.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["VATRate"] == {"ID": 5}


def test_build_rows_vat_rate_0_percent():
    """0% tax rate maps to VatRate ID 1."""
    inv = _make_invoice(line_items=[{"description": "Test", "tax_rate": "0"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["VATRate"] == {"ID": 1}


def test_build_rows_unknown_vat_rate_omitted():
    """Unknown VAT rate (e.g. 25%) does not produce VATRate entry."""
    inv = _make_invoice(line_items=[{"description": "Test", "tax_rate": "25.00"}])
    rows = _build_invoice_rows(inv)
    assert "VATRate" not in rows[0]


def test_build_rows_missing_optional_fields_omitted():
    """Optional row fields are omitted when not present in the line item."""
    inv = _make_invoice(line_items=[{"description": "Samo opis"}])
    rows = _build_invoice_rows(inv)
    row = rows[0]
    assert "Value" not in row
    assert "Quantity" not in row
    assert "Price" not in row
    assert "VATRate" not in row


def test_build_rows_skips_non_dict_items():
    """Non-dict entries in line_items are silently skipped."""
    inv = _make_invoice(line_items=["not a dict", 42, None, {"description": "Validan unos"}])
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    assert rows[0]["Description"] == "Validan unos"


def test_build_rows_empty_list_falls_back_to_totals():
    """Empty line_items list falls back to single row from invoice subtotal."""
    inv = _make_invoice(
        invoice_number="RE-002",
        total_amount=Decimal("6000.00"),
        subtotal=Decimal("5000.00"),
        line_items=[],
    )
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    assert rows[0]["Value"] == pytest.approx(5000.0)
    assert "Faktura RE-002" in rows[0]["Description"]


def test_build_rows_fallback_description_format():
    """Fallback row description includes 'Faktura' and the invoice number."""
    inv = _make_invoice(invoice_number="INV-2026-042", total_amount=Decimal("1000.00"))
    inv.line_items = None
    rows = _build_invoice_rows(inv)
    assert rows[0]["Description"] == "Faktura INV-2026-042"


def test_build_rows_fallback_no_vat_when_none():
    """Fallback row omits VATRate when invoice tax_rate is None."""
    inv = _make_invoice(total_amount=Decimal("1000.00"))
    inv.line_items = None
    inv.tax_rate = None
    inv.subtotal = None
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    assert "VATRate" not in rows[0]


def test_build_rows_multiple_line_items_all_fields():
    """Multiple line items with all fields produce correct row dicts."""
    inv = _make_invoice(
        line_items=[
            {
                "description": "Stavka A",
                "total": "2400.00",
                "unit_price": "2000.00",
                "quantity": 1,
                "tax_rate": "20.00",
            },
            {
                "description": "Stavka B",
                "total": "600.00",
                "unit_price": "500.00",
                "quantity": 1,
                "tax_rate": "20.00",
            },
        ]
    )
    rows = _build_invoice_rows(inv)
    assert rows[0]["Description"] == "Stavka A"
    assert rows[0]["Value"] == pytest.approx(2400.0)
    assert rows[1]["Description"] == "Stavka B"
    assert rows[1]["Value"] == pytest.approx(600.0)


def test_build_rows_none_line_items_with_totals():
    """None line_items with total fields produces a complete fallback row."""
    inv = _make_invoice(
        invoice_number="RE-999",
        total_amount=Decimal("11800.00"),
        subtotal=Decimal("10000.00"),
        tax_rate=Decimal("20.00"),
    )
    inv.line_items = None
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    row = rows[0]
    assert row["Value"] == pytest.approx(10000.0)
    assert row["VATRate"] == {"ID": 4}


# ===========================================================================
# D. Payload structure
# ===========================================================================


def test_map_invoice_complete_payload_structure():
    """Full payload contains all expected top-level keys."""
    inv = _make_invoice(
        invoice_number="RE-2026-001",
        invoice_date=date(2026, 3, 1),
        due_date=date(2026, 3, 31),
        total_amount=Decimal("12000.00"),
        line_items=[{"description": "Usluge", "total": "12000.00", "tax_rate": "20.00"}],
    )
    payload = map_invoice_to_received(inv, customer_id=7, currency_id=3)

    assert "DocumentReference" in payload
    assert "Customer" in payload
    assert "PaymentType" in payload
    assert "DateIssued" in payload
    assert "DateDue" in payload
    assert "InvoiceAmount" in payload
    assert "InvoiceAmountDomesticCurrency" in payload
    assert "Currency" in payload
    assert "ReceivedInvoiceRows" in payload


def test_map_invoice_row_count_matches_line_items():
    """Number of rows matches number of valid line item dicts."""
    items = [{"description": f"Stavka {i}", "total": str(i * 1000)} for i in range(1, 6)]
    inv = _make_invoice(line_items=items)
    payload = map_invoice_to_received(inv, customer_id=1)
    assert len(payload["ReceivedInvoiceRows"]) == 5


# ===========================================================================
# E. Validator
# ===========================================================================


def test_validate_valid_invoice_no_errors():
    """A complete invoice has no blocking errors."""
    inv = _make_invoice()
    result = validate_invoice_for_minimax(inv)
    assert len(result["errors"]) == 0


def test_validate_missing_pib():
    """Missing seller PIB is a blocking error."""
    inv = _make_invoice(seller={"name": "No PIB DOO"})
    result = validate_invoice_for_minimax(inv)
    assert any("PIB" in e for e in result["errors"])


def test_validate_missing_invoice_number():
    """Missing invoice number is a blocking error."""
    inv = _make_invoice()
    inv.invoice_number = None
    result = validate_invoice_for_minimax(inv)
    assert any("broj fakture" in e.lower() for e in result["errors"])


def test_validate_missing_date():
    """Missing invoice date is a blocking error."""
    inv = _make_invoice()
    inv.invoice_date = None
    result = validate_invoice_for_minimax(inv)
    assert any("datum" in e.lower() for e in result["errors"])


def test_validate_missing_total():
    """Missing total amount is a blocking error."""
    inv = _make_invoice()
    inv.total_amount = None
    result = validate_invoice_for_minimax(inv)
    assert any("iznos" in e.lower() for e in result["errors"])


def test_validate_missing_due_date_is_warning():
    """Missing due date is a warning, not a blocking error."""
    inv = _make_invoice()
    inv.due_date = None
    result = validate_invoice_for_minimax(inv)
    assert len(result["errors"]) == 0
    assert any("datum dospeća" in w.lower() for w in result["warnings"])
