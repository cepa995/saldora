"""Map Saldora Invoice models to MiniMax API payloads.

Field names and IDs discovered from the MiniMax RS Swagger API spec
and validated against org 91103.

MiniMax ReceivedInvoice required fields (from API probing):
  - DocumentReference (string) — original invoice number
  - Customer (FK {ID: int}) — must exist in MiniMax
  - Currency (FK {ID: int}) — must exist; RSD = ID 2
  - PaymentType (string) — must be D/Z/P/R/N
  - DateIssued (datetime string) — invoice issue date
  - DateTransaction (datetime string) — goods/services date
  - DateDue (datetime string) — payment due date
  - DateReceived (datetime string) — date invoice was received
  - InvoiceAmount (number) — total amount, rounded to 2 decimals
  - InvoiceAmountDomesticCurrency (number) — same sign, same decimals as InvoiceAmount

MiniMax Customer required fields:
  - Name (string)
  - Country (FK {ID: int}) — Serbia = ID 3
  - CountryName (string) — print name, e.g. "Republika Srbija"
  - Currency (FK {ID: int}) — RSD = ID 2
  - SubjectToVAT (string) — "D" or "N" (not Y/N)
  - PostalCode (string) — required, non-empty
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

# MiniMax reference IDs for Serbia (RS)
COUNTRY_RS_ID = 3  # Republika Srbija
COUNTRY_RS_NAME = "Republika Srbija"
CURRENCY_RSD_ID = 2  # Serbian Dinar

# VAT rate mapping: Saldora percentage → MiniMax VatRate ID
VAT_RATE_MAP = {
    20: 4,  # Code "S" — standard rate
    10: 5,  # Code "Z" — reduced rate
    8: 3,   # Code "P" — special reduced rate
    0: 1,   # Code "N" — exempt
}

# Valid payment types in MiniMax
VALID_PAYMENT_TYPES = {"D", "Z", "P", "R", "N"}


def validate_invoice_for_minimax(invoice: Invoice) -> dict:
    """Validate that an invoice meets ALL MiniMax API requirements.

    Checks every field that MiniMax validates server-side, so we can
    give clear Serbian error messages instead of cryptic 409 responses.

    Args:
        invoice: Invoice model instance.

    Returns:
        Dict with "errors" (blockers) and "warnings" (informational).
        Empty errors list = OK to push.
    """
    errors: list[str] = []
    warnings: list[str] = []

    seller = invoice.seller if isinstance(invoice.seller, dict) else {}

    # --- Customer creation requirements ---

    if not seller.get("pib"):
        errors.append("Nedostaje PIB prodavca (potreban za kreiranje stranke u MiniMax-u)")

    if not seller.get("name"):
        errors.append("Nedostaje naziv prodavca")

    if not seller.get("postal_code"):
        warnings.append(
            "Nedostaje poštanski broj prodavca — koristiće se podrazumevana vrednost"
        )

    # --- Invoice header requirements ---

    if not invoice.invoice_number:
        errors.append("Nedostaje broj fakture (MiniMax: originalni broj je obavezan)")

    if not invoice.invoice_date:
        errors.append("Nedostaje datum fakture (MiniMax: datum izdavanja je obavezan)")

    if invoice.total_amount is None:
        errors.append("Nedostaje ukupan iznos fakture (MiniMax: iznos računa je obavezan)")
    else:
        amount = float(invoice.total_amount)
        if round(amount, 2) != amount and abs(amount - round(amount, 2)) > 0.005:
            errors.append("Iznos fakture mora biti zaokružen na 2 decimale za MiniMax")

    has_items = (
        invoice.line_items
        and isinstance(invoice.line_items, list)
        and len(invoice.line_items) > 0
    )
    if not has_items and invoice.total_amount is None:
        errors.append("Nedostaje iznos ili stavke fakture")

    if has_items:
        for i, item in enumerate(invoice.line_items, 1):
            if not isinstance(item, dict):
                continue
            has_value = (
                item.get("tax_base") is not None
                or item.get("total") is not None
                or (
                    item.get("unit_price") is not None
                    and item.get("quantity") is not None
                )
            )
            if not has_value:
                errors.append(
                    f"Stavka {i}: nedostaje iznos "
                    "(potreban tax_base, total, ili unit_price + quantity)"
                )

    if has_items:
        for i, item in enumerate(invoice.line_items, 1):
            if not isinstance(item, dict):
                continue
            rate = item.get("tax_rate")
            if rate is not None:
                rounded = round(float(rate))
                if rounded not in VAT_RATE_MAP:
                    errors.append(
                        f"Stavka {i}: nepoznata stopa PDV-a {rate}% "
                        f"(MiniMax podržava: {', '.join(str(r) + '%' for r in sorted(VAT_RATE_MAP))})"
                    )

    if not invoice.due_date:
        warnings.append("Nedostaje datum dospeća — koristiće se datum fakture + 30 dana")

    return {"errors": errors, "warnings": warnings}


def build_customer_payload(
    name: str,
    pib: str,
    address: str = "",
    city: str = "",
    postal_code: str = "",
) -> dict:
    """Build a MiniMax Customer creation payload with all required fields.

    Args:
        name: Company name.
        pib: Tax identification number (PIB).
        address: Street address.
        city: City name.
        postal_code: Postal code (required by MiniMax).

    Returns:
        Dict ready to POST to /customers endpoint.
    """
    return {
        "Name": name or "Nepoznat",
        "TaxNumber": pib,
        "Address": address or "",
        "City": city or "",
        "PostalCode": postal_code or "00000",
        "Country": {"ID": COUNTRY_RS_ID},
        "CountryName": COUNTRY_RS_NAME,
        "Currency": {"ID": CURRENCY_RSD_ID},
        "SubjectToVAT": "D",
    }


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

    # Dates (all required by MiniMax)
    if invoice.invoice_date:
        date_str = invoice.invoice_date.isoformat() + "T00:00:00"
        payload["DateIssued"] = date_str
        payload["DateReceived"] = date_str
        payload["DateTransaction"] = date_str

    if invoice.due_date:
        payload["DateDue"] = invoice.due_date.isoformat() + "T00:00:00"
    elif invoice.invoice_date:
        from datetime import timedelta

        due = invoice.invoice_date + timedelta(days=30)
        payload["DateDue"] = due.isoformat() + "T00:00:00"

    # Amounts (must be rounded to 2 decimals, domestic = same for RSD)
    if invoice.total_amount is not None:
        amount = round(float(invoice.total_amount), 2)
        payload["InvoiceAmount"] = amount
        payload["InvoiceAmountDomesticCurrency"] = amount

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
            "Value": round(float(invoice.subtotal or invoice.total_amount), 2),
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

        # Use tax_base (poreska osnovica) if available, otherwise total or qty * price
        tax_base = item.get("tax_base")
        total = item.get("total")
        unit_price = item.get("unit_price")
        quantity = item.get("quantity")

        if tax_base is not None:
            row["Value"] = round(float(tax_base), 2)
        elif total is not None:
            row["Value"] = round(float(total), 2)
        elif unit_price is not None and quantity is not None:
            row["Value"] = round(float(unit_price) * float(quantity), 2)

        if quantity is not None:
            row["Quantity"] = round(float(quantity), 4)

        if unit_price is not None:
            row["Price"] = round(float(unit_price), 4)

        # Map VAT rate to MiniMax FK reference
        vat_ref = _map_vat_rate(item.get("tax_rate"))
        if vat_ref:
            row["VATRate"] = vat_ref

        rows.append(row)

    return rows
