"""Unit tests for the MiniMax invoice mapper.

Tests cover map_invoice_to_received and _build_invoice_rows. These are pure
mapping functions — no database, Redis, or HTTP calls are needed.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.invoice import Invoice
from app.services.minimax.mapper import _build_invoice_rows, map_invoice_to_received

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
    inv.seller = kwargs.get("seller", {"name": "Dobavljač DOO", "pib": "123456789"})
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


def test_map_invoice_status_verified():
    """Verified invoice maps to Status 'P' (Plačeno/Posted)."""
    inv = _make_invoice(status="verified")
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["Status"] == "P"


def test_map_invoice_status_review():
    """Non-verified invoice maps to Status 'O' (Open)."""
    inv = _make_invoice(status="review")
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["Status"] == "O"


def test_map_invoice_status_processing():
    """Processing invoice maps to Status 'O'."""
    inv = _make_invoice(status="processing")
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["Status"] == "O"


def test_map_invoice_dates_present():
    """DateIssued, DateReceived, and DateTransaction are set from invoice_date."""
    inv = _make_invoice(invoice_date=date(2026, 3, 1))
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DateIssued"] == "2026-03-01"
    assert payload["DateReceived"] == "2026-03-01"
    assert payload["DateTransaction"] == "2026-03-01"


def test_map_invoice_due_date():
    """DateDue is set when due_date is present."""
    inv = _make_invoice(due_date=date(2026, 3, 31))
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DateDue"] == "2026-03-31"


def test_map_invoice_no_invoice_date():
    """Date fields are omitted when invoice_date is None."""
    inv = _make_invoice()
    inv.invoice_date = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "DateIssued" not in payload
    assert "DateReceived" not in payload
    assert "DateTransaction" not in payload


def test_map_invoice_no_due_date():
    """DateDue is omitted when due_date is None."""
    inv = _make_invoice()
    inv.due_date = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "DateDue" not in payload


def test_map_invoice_total_amount():
    """InvoiceAmount is set as float from total_amount."""
    inv = _make_invoice(total_amount=Decimal("12000.00"))
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["InvoiceAmount"] == pytest.approx(12000.0)
    assert isinstance(payload["InvoiceAmount"], float)


def test_map_invoice_no_total_amount():
    """InvoiceAmount is omitted when total_amount is None."""
    inv = _make_invoice()
    inv.total_amount = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert "InvoiceAmount" not in payload


def test_map_invoice_with_currency_id():
    """Currency.ID is included when currency_id is provided."""
    inv = _make_invoice()
    payload = map_invoice_to_received(inv, customer_id=1, currency_id=5)
    assert payload["Currency"]["ID"] == 5


def test_map_invoice_without_currency_id():
    """Currency key is omitted when currency_id is None."""
    inv = _make_invoice()
    payload = map_invoice_to_received(inv, customer_id=1, currency_id=None)
    assert "Currency" not in payload


def test_map_invoice_empty_invoice_number():
    """None invoice_number maps to empty string for DocumentReference."""
    inv = _make_invoice()
    inv.invoice_number = None
    payload = map_invoice_to_received(inv, customer_id=1)
    assert payload["DocumentReference"] == ""


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
                "tax_amount": "2000.00",
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
    """Single fallback row is created from totals when line_items is None."""
    inv = _make_invoice(
        invoice_number="RE-001",
        total_amount=Decimal("12000.00"),
        subtotal=Decimal("10000.00"),
        tax_rate=Decimal("20.00"),
        tax_amount=Decimal("2000.00"),
    )
    inv.line_items = None
    payload = map_invoice_to_received(inv, customer_id=1)
    rows = payload["ReceivedInvoiceRows"]
    assert len(rows) == 1
    assert rows[0]["Value"] == pytest.approx(12000.0)
    assert rows[0]["VATRate"] == pytest.approx(20.0)
    assert rows[0]["ValueBase"] == pytest.approx(10000.0)
    assert rows[0]["VATAmount"] == pytest.approx(2000.0)


# ===========================================================================
# C. _build_invoice_rows — line items
# ===========================================================================


def test_build_rows_from_line_items():
    """Line items produce one row dict per item."""
    inv = _make_invoice(
        line_items=[
            {
                "description": "Konsultantske usluge",
                "total": "5000.00",
                "unit_price": "5000.00",
                "quantity": 1,
                "tax_rate": "20.00",
                "tax_amount": "1000.00",
            },
            {
                "description": "Softverska licenca",
                "total": "3000.00",
                "unit_price": "1500.00",
                "quantity": 2,
                "tax_rate": "20.00",
                "tax_amount": "600.00",
            },
        ]
    )
    rows = _build_invoice_rows(inv)
    assert len(rows) == 2


def test_build_rows_description():
    """Row Description is mapped from line item description."""
    inv = _make_invoice(line_items=[{"description": "Gorivo dizel"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Description"] == "Gorivo dizel"


def test_build_rows_value():
    """Row Value is mapped from line item total as float."""
    inv = _make_invoice(line_items=[{"description": "Test", "total": "8500.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Value"] == pytest.approx(8500.0)
    assert isinstance(rows[0]["Value"], float)


def test_build_rows_value_base():
    """Row ValueBase is mapped from unit_price."""
    inv = _make_invoice(line_items=[{"description": "Test", "unit_price": "4250.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["ValueBase"] == pytest.approx(4250.0)


def test_build_rows_quantity():
    """Row Quantity is mapped from item quantity as float."""
    inv = _make_invoice(line_items=[{"description": "Test", "quantity": 3}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["Quantity"] == pytest.approx(3.0)


def test_build_rows_vat_rate():
    """Row VATRate is mapped from item tax_rate."""
    inv = _make_invoice(line_items=[{"description": "Test", "tax_rate": "20.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["VATRate"] == pytest.approx(20.0)


def test_build_rows_vat_amount():
    """Row VATAmount is mapped from item tax_amount."""
    inv = _make_invoice(line_items=[{"description": "Test", "tax_amount": "1000.00"}])
    rows = _build_invoice_rows(inv)
    assert rows[0]["VATAmount"] == pytest.approx(1000.0)


def test_build_rows_missing_optional_fields_omitted():
    """Optional row fields are omitted when not present in the line item."""
    inv = _make_invoice(line_items=[{"description": "Samo opis"}])
    rows = _build_invoice_rows(inv)
    row = rows[0]
    assert "Value" not in row
    assert "ValueBase" not in row
    assert "Quantity" not in row
    assert "VATRate" not in row
    assert "VATAmount" not in row


def test_build_rows_skips_non_dict_items():
    """Non-dict entries in line_items are silently skipped."""
    inv = _make_invoice(line_items=["not a dict", 42, None, {"description": "Validan unos"}])
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    assert rows[0]["Description"] == "Validan unos"


def test_build_rows_empty_list_falls_back_to_totals():
    """Empty line_items list falls back to single row from invoice totals."""
    inv = _make_invoice(
        invoice_number="RE-002",
        total_amount=Decimal("5000.00"),
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


def test_build_rows_fallback_no_tax_fields_when_none():
    """Fallback row omits VATRate/ValueBase/VATAmount when invoice fields are None."""
    inv = _make_invoice(total_amount=Decimal("1000.00"))
    inv.line_items = None
    inv.tax_rate = None
    inv.subtotal = None
    inv.tax_amount = None
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    assert "VATRate" not in rows[0]
    assert "ValueBase" not in rows[0]
    assert "VATAmount" not in rows[0]


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
                "tax_amount": "400.00",
            },
            {
                "description": "Stavka B",
                "total": "600.00",
                "unit_price": "500.00",
                "quantity": 1,
                "tax_rate": "20.00",
                "tax_amount": "100.00",
            },
        ]
    )
    rows = _build_invoice_rows(inv)
    assert rows[0]["Description"] == "Stavka A"
    assert rows[0]["Value"] == pytest.approx(2400.0)
    assert rows[1]["Description"] == "Stavka B"
    assert rows[1]["Value"] == pytest.approx(600.0)


def test_build_rows_none_line_items_with_totals():
    """None line_items with all total fields produces a complete fallback row."""
    inv = _make_invoice(
        invoice_number="RE-999",
        total_amount=Decimal("11800.00"),
        subtotal=Decimal("10000.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=Decimal("1800.00"),
    )
    inv.line_items = None
    rows = _build_invoice_rows(inv)
    assert len(rows) == 1
    row = rows[0]
    assert row["Value"] == pytest.approx(11800.0)
    assert row["ValueBase"] == pytest.approx(10000.0)
    assert row["VATRate"] == pytest.approx(18.0)
    assert row["VATAmount"] == pytest.approx(1800.0)


# ===========================================================================
# D. Edge cases
# ===========================================================================


def test_map_invoice_complete_payload_structure():
    """Full payload contains all expected top-level keys."""
    inv = _make_invoice(
        invoice_number="RE-2026-001",
        status="verified",
        invoice_date=date(2026, 3, 1),
        due_date=date(2026, 3, 31),
        total_amount=Decimal("12000.00"),
        line_items=[{"description": "Usluge", "total": "12000.00", "tax_rate": "20.00"}],
    )
    payload = map_invoice_to_received(inv, customer_id=7, currency_id=3)

    assert "DocumentReference" in payload
    assert "Customer" in payload
    assert "Status" in payload
    assert "DateIssued" in payload
    assert "DateDue" in payload
    assert "InvoiceAmount" in payload
    assert "Currency" in payload
    assert "ReceivedInvoiceRows" in payload


def test_map_invoice_row_count_matches_line_items():
    """Number of rows matches number of valid line item dicts."""
    items = [{"description": f"Stavka {i}", "total": str(i * 1000)} for i in range(1, 6)]
    inv = _make_invoice(line_items=items)
    payload = map_invoice_to_received(inv, customer_id=1)
    assert len(payload["ReceivedInvoiceRows"]) == 5
