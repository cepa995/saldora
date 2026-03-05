"""Map FakturaAI Invoice models to MiniMax API payloads."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def map_invoice_to_received(
    invoice: Invoice,
    customer_id: int,
    currency_id: int | None = None,
) -> dict:
    """Map a FakturaAI Invoice to a MiniMax ReceivedInvoice payload.

    Args:
        invoice: Invoice model instance.
        customer_id: MiniMax customer ID (from find_or_create_customer).
        currency_id: MiniMax currency ID (optional, looked up beforehand).

    Returns:
        Dict ready to POST to /receivedinvoices endpoint.
    """
    payload: dict = {
        "DocumentReference": invoice.invoice_number or "",
        "Customer": {"ID": customer_id},
        "Status": "P" if invoice.status == "verified" else "O",
    }

    if invoice.invoice_date:
        payload["DateIssued"] = invoice.invoice_date.isoformat()
        payload["DateReceived"] = invoice.invoice_date.isoformat()
        payload["DateTransaction"] = invoice.invoice_date.isoformat()

    if invoice.due_date:
        payload["DateDue"] = invoice.due_date.isoformat()

    if invoice.total_amount is not None:
        payload["InvoiceAmount"] = float(invoice.total_amount)

    if currency_id:
        payload["Currency"] = {"ID": currency_id}

    # Add line items (rows)
    rows = _build_invoice_rows(invoice)
    if rows:
        payload["ReceivedInvoiceRows"] = rows

    return payload


def _build_invoice_rows(invoice: Invoice) -> list[dict]:
    """Build ReceivedInvoice row entries from line items.

    Args:
        invoice: Invoice with optional line_items.

    Returns:
        List of row dicts for the MiniMax API.
    """
    if not invoice.line_items or not isinstance(invoice.line_items, list):
        # Fall back to single row from totals
        if invoice.total_amount is None:
            return []
        row = {
            "Description": f"Faktura {invoice.invoice_number or ''}".strip(),
            "Value": float(invoice.total_amount),
        }
        if invoice.tax_rate is not None:
            row["VATRate"] = float(invoice.tax_rate)
        if invoice.subtotal is not None:
            row["ValueBase"] = float(invoice.subtotal)
        if invoice.tax_amount is not None:
            row["VATAmount"] = float(invoice.tax_amount)
        return [row]

    rows = []
    for item in invoice.line_items:
        if not isinstance(item, dict):
            continue
        row: dict = {
            "Description": item.get("description", ""),
        }

        total = item.get("total")
        if total is not None:
            row["Value"] = float(total)

        unit_price = item.get("unit_price")
        if unit_price is not None:
            row["ValueBase"] = float(unit_price)

        quantity = item.get("quantity")
        if quantity is not None:
            row["Quantity"] = float(quantity)

        tax_rate = item.get("tax_rate")
        if tax_rate is not None:
            row["VATRate"] = float(tax_rate)

        tax_amount = item.get("tax_amount")
        if tax_amount is not None:
            row["VATAmount"] = float(tax_amount)

        rows.append(row)

    return rows
