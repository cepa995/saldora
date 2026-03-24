"""Map Saldora Invoice models to MiniMax API payloads.

Field names and IDs discovered from the MiniMax RS Swagger API spec
and validated against org 91103.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

# MiniMax reference IDs for Serbia (RS)
COUNTRY_RS_ID = 3  # Republika Srbija
CURRENCY_RSD_ID = 2  # Serbian Dinar

# VAT rate mapping: Saldora percentage → MiniMax VatRate ID
VAT_RATE_MAP = {
    20: 4,  # Code "S" — standard rate
    10: 5,  # Code "Z" — reduced rate
    8: 3,  # Code "P" — special reduced rate
    0: 1,  # Code "N" — exempt
}


def validate_invoice_for_minimax(invoice: Invoice) -> list[str]:
    """Validate that an invoice has all required fields for MiniMax push.

    Args:
        invoice: Invoice model instance.

    Returns:
        List of validation error messages. Empty list = valid.
    """
    errors: list[str] = []

    # Required: seller PIB (used to find/create customer)
    seller = invoice.seller if isinstance(invoice.seller, dict) else {}
    if not seller.get("pib"):
        errors.append("Nedostaje PIB prodavca")

    # Required: original document number
    if not invoice.invoice_number:
        errors.append("Nedostaje broj fakture (DocumentReference)")

    # Required: invoice date
    if not invoice.invoice_date:
        errors.append("Nedostaje datum fakture")

    # Required: at least one line item or total amount
    has_items = (
        invoice.line_items and isinstance(invoice.line_items, list) and len(invoice.line_items) > 0
    )
    if not has_items and invoice.total_amount is None:
        errors.append("Nedostaje iznos ili stavke fakture")

    # Warning: missing due date (MiniMax accepts it but it's useful)
    if not invoice.due_date:
        errors.append("Nedostaje datum dospeća (opcionalno ali preporučeno)")

    # Warning: missing seller name
    if not seller.get("name"):
        errors.append("Nedostaje naziv prodavca (koristiće se 'Nepoznat')")

    return errors


def map_invoice_to_received(
    invoice: Invoice,
    customer_id: int,
    currency_id: int | None = None,
) -> dict:
    """Map a Saldora Invoice to a MiniMax ReceivedInvoice payload.

    Uses field names from the MiniMax RS Swagger API spec.

    Args:
        invoice: Invoice model instance.
        customer_id: MiniMax customer ID (from find_or_create_customer).
        currency_id: MiniMax currency ID (default: RSD=2).

    Returns:
        Dict ready to POST to /receivedinvoices endpoint.
    """
    payload: dict = {
        "DocumentReference": invoice.invoice_number or "N/A",
        "Customer": {"ID": customer_id},
        "Currency": {"ID": currency_id or CURRENCY_RSD_ID},
        "PaymentType": "N",  # N=Neplaćen (unpaid) — default for received invoices
    }

    if invoice.invoice_date:
        date_str = invoice.invoice_date.isoformat() + "T00:00:00"
        payload["DateIssued"] = date_str
        payload["DateReceived"] = date_str
        payload["DateTransaction"] = date_str

    if invoice.due_date:
        payload["DateDue"] = invoice.due_date.isoformat() + "T00:00:00"
    elif invoice.invoice_date:
        # Default: 30 days from invoice date
        from datetime import timedelta

        due = invoice.invoice_date + timedelta(days=30)
        payload["DateDue"] = due.isoformat() + "T00:00:00"

    if invoice.total_amount is not None:
        payload["InvoiceAmount"] = float(invoice.total_amount)

    # Line items
    rows = _build_invoice_rows(invoice)
    if rows:
        payload["ReceivedInvoiceRows"] = rows

    return payload


def _map_vat_rate(rate_percent: float | int | None) -> dict | None:
    """Map a VAT percentage to a MiniMax VATRate FK reference.

    Args:
        rate_percent: VAT rate as percentage (0, 8, 10, 20).

    Returns:
        MiniMax FK dict like {"ID": 4} or None if unknown rate.
    """
    if rate_percent is None:
        return None
    rounded = round(float(rate_percent))
    vat_id = VAT_RATE_MAP.get(rounded)
    if vat_id:
        return {"ID": vat_id}
    logger.warning("Unknown VAT rate %s%% — skipping VATRate field", rate_percent)
    return None


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
        row: dict = {
            "Description": f"Faktura {invoice.invoice_number or ''}".strip(),
            "Value": float(invoice.subtotal or invoice.total_amount),
        }
        vat_ref = _map_vat_rate(invoice.tax_rate)
        if vat_ref:
            row["VATRate"] = vat_ref
        return [row]

    rows = []
    for item in invoice.line_items:
        if not isinstance(item, dict):
            continue

        row = {
            "Description": item.get("description", "Stavka"),
        }

        # Use tax_base (poreska osnovica) if available, otherwise unit_price * qty
        tax_base = item.get("tax_base")
        total = item.get("total")
        unit_price = item.get("unit_price")
        quantity = item.get("quantity")

        if tax_base is not None:
            row["Value"] = float(tax_base)
        elif total is not None:
            row["Value"] = float(total)

        if quantity is not None:
            row["Quantity"] = float(quantity)

        if unit_price is not None:
            row["Price"] = float(unit_price)

        # Map VAT rate to MiniMax FK reference
        vat_ref = _map_vat_rate(item.get("tax_rate"))
        if vat_ref:
            row["VATRate"] = vat_ref

        rows.append(row)

    return rows
