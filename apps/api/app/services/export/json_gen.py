"""JSON export generator with flat and nested modes."""

import json
import logging
from decimal import Decimal
from io import BytesIO

from app.models.invoice import Invoice
from app.services.export.core import (
    extract_invoice_row,
)

logger = logging.getLogger(__name__)


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts Decimals to floats."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def generate_json(
    invoices: list[Invoice],
    nested: bool = False,
    date_format: str = "DD.MM.YYYY",
    decimal_separator: str = ".",
) -> BytesIO:
    """Generate JSON export.

    Args:
        invoices: List of Invoice instances (with accounting_intent loaded).
        nested: If True, include line_items and accounting_intent.
        date_format: Date format string.
        decimal_separator: Decimal separator (always '.' for JSON).

    Returns:
        BytesIO buffer containing the JSON file.
    """
    # JSON always uses '.' for decimals
    records = []

    for inv in invoices:
        if nested:
            record = _build_nested_record(inv)
        else:
            record = extract_invoice_row(inv, date_format, ".")

        records.append(record)

    buffer = BytesIO()
    buffer.write(
        json.dumps(records, ensure_ascii=False, indent=2, cls=_DecimalEncoder).encode("utf-8")
    )
    buffer.seek(0)
    return buffer


def _build_nested_record(inv: Invoice) -> dict:
    """Build a nested JSON record with line items and accounting intent.

    Args:
        inv: Invoice model instance.

    Returns:
        Dict with all invoice data including nested objects.
    """
    seller = inv.seller if isinstance(inv.seller, dict) else {}
    buyer = inv.buyer if isinstance(inv.buyer, dict) else {}

    record = {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "seller": {
            "name": seller.get("name"),
            "pib": seller.get("pib"),
            "address": seller.get("address"),
            "city": seller.get("city"),
        },
        "buyer": {
            "name": buyer.get("name"),
            "pib": buyer.get("pib"),
            "address": buyer.get("address"),
            "city": buyer.get("city"),
        },
        "subtotal": float(inv.subtotal) if inv.subtotal is not None else None,
        "tax_rate": float(inv.tax_rate) if inv.tax_rate is not None else None,
        "tax_amount": float(inv.tax_amount) if inv.tax_amount is not None else None,
        "total_amount": float(inv.total_amount) if inv.total_amount is not None else None,
        "currency": inv.currency,
        "status": inv.status,
        "confidence_score": float(inv.confidence_score) if inv.confidence_score else None,
        "line_items": inv.line_items or [],
        "tax_groups": inv.tax_groups or [],
    }

    # Add accounting intent if available
    intent = inv.accounting_intent
    if intent:
        record["accounting_intent"] = {
            "document_type": intent.document_type,
            "transaction_type": intent.transaction_type,
            "vat_treatment": intent.vat_treatment,
            "is_deductible": intent.is_deductible,
            "vat_breakdown": intent.vat_breakdown,
            "suggested_konta": intent.suggested_konta,
            "pdv_book_entries": intent.pdv_book_entries,
            "confidence": float(intent.confidence),
            "requires_review": intent.requires_review,
        }

    return record
