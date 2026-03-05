"""Export orchestration — validate, block-check, dispatch to generators."""

import logging
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

# Serbian column headers for invoice export
INVOICE_HEADERS_SR = {
    "invoice_number": "Broj fakture",
    "invoice_date": "Datum fakture",
    "due_date": "Datum valute",
    "seller_name": "Prodavac",
    "seller_pib": "PIB prodavca",
    "seller_address": "Adresa prodavca",
    "seller_city": "Grad prodavca",
    "buyer_name": "Kupac",
    "buyer_pib": "PIB kupca",
    "subtotal": "Osnovica",
    "tax_rate": "Stopa PDV (%)",
    "tax_amount": "Iznos PDV",
    "total_amount": "Ukupan iznos",
    "currency": "Valuta",
    "status": "Status",
    "confidence_score": "Pouzdanost (%)",
}

# Valid field keys for custom templates (keys from INVOICE_HEADERS_SR)
VALID_FIELD_KEYS = set(INVOICE_HEADERS_SR.keys())

# Serbian column headers for line items
LINE_ITEM_HEADERS_SR = {
    "invoice_number": "Broj fakture",
    "description": "Opis",
    "quantity": "Kolicina",
    "unit_price": "Jedinicna cena",
    "total": "Ukupno",
    "tax_rate": "Stopa PDV (%)",
    "tax_amount": "Iznos PDV",
}

# Serbian column headers for accounting data
ACCOUNTING_HEADERS_SR = {
    "invoice_number": "Broj fakture",
    "document_type": "Vrsta dokumenta",
    "transaction_type": "Vrsta transakcije",
    "vat_treatment": "PDV tretman",
    "is_deductible": "Odbitni PDV",
    "confidence": "Pouzdanost (%)",
    "requires_review": "Potrebna revizija",
    "debit_konta": "Konta duguje",
    "credit_konta": "Konta potrazuje",
}

# Status labels in Serbian
STATUS_LABELS_SR = {
    "processing": "U obradi",
    "review": "Na pregledu",
    "verified": "Verifikovana",
    "exported": "Izvezena",
    "error": "Greska",
}


class ExportBlockedError(Exception):
    """Raised when one or more invoices fail export blocking rules."""

    def __init__(self, blocked_invoices: list[dict]):
        self.blocked_invoices = blocked_invoices
        super().__init__(f"{len(blocked_invoices)} invoice(s) blocked from export")


async def load_invoices_for_export(
    db: AsyncSession,
    invoice_ids: list[UUID],
    organization_id: UUID,
) -> list[Invoice]:
    """Load invoices with accounting_intent eagerly, scoped by org.

    Args:
        db: Database session.
        invoice_ids: List of invoice UUIDs to export.
        organization_id: Organization UUID for tenant isolation.

    Returns:
        List of Invoice model instances with accounting_intent loaded.

    Raises:
        ValueError: If any invoice_id not found or not owned by org.
    """
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.accounting_intent))
        .where(
            Invoice.id.in_(invoice_ids),
            Invoice.organization_id == organization_id,
        )
    )
    invoices = result.unique().scalars().all()

    found_ids = {inv.id for inv in invoices}
    missing = set(invoice_ids) - found_ids
    if missing:
        raise ValueError(f"Fakture nisu pronadjene: {', '.join(str(m) for m in missing)}")

    return list(invoices)


def check_export_blocking(
    invoices: list[Invoice],
    export_format: str | None = None,
) -> list[dict]:
    """Apply SRS 4.9.7 export blocking rules.

    Args:
        invoices: List of Invoice instances to check.
        export_format: Target export format (e.g. 'minimax_xml').
            MiniMax XML has stricter rules requiring verified status.

    Returns:
        List of dicts with {invoice_id, invoice_number, reasons} for blocked
        invoices. Empty list means all invoices pass.
    """
    blocked = []
    for inv in invoices:
        reasons = []

        # Rule 1: Required fields
        if not inv.invoice_number:
            reasons.append("Nedostaje broj fakture")
        if not inv.invoice_date:
            reasons.append("Nedostaje datum fakture")
        if not inv.total_amount:
            reasons.append("Nedostaje ukupan iznos")

        seller = inv.seller if isinstance(inv.seller, dict) else {}
        if not seller.get("pib"):
            reasons.append("Nedostaje PIB prodavca")

        # Rule 2: Confidence < 60% without verification
        if inv.confidence_score is not None:
            score = float(inv.confidence_score)
            if score < 60 and inv.status != "verified":
                reasons.append(f"Nizak nivo pouzdanosti ({score:.0f}%) bez verifikacije")

        # Rule 3: Unresolved blocking warnings
        if inv.warnings and inv.status not in ("verified", "exported"):
            has_blocking = any(isinstance(w, dict) and w.get("blocking") for w in inv.warnings)
            if has_blocking:
                reasons.append("Nerazresena blokirajuca upozorenja")

        # Rule 4: MiniMax XML requires verified or exported status
        if export_format == "minimax_xml" and inv.status not in ("verified", "exported"):
            reasons.append("Faktura mora biti verifikovana pre izvoza u MiniMax XML format")

        if reasons:
            blocked.append(
                {
                    "invoice_id": str(inv.id),
                    "invoice_number": inv.invoice_number or "N/A",
                    "reasons": reasons,
                }
            )

    return blocked


def format_serbian_date(d: date | None, fmt: str = "DD.MM.YYYY") -> str:
    """Format a date using Serbian convention.

    Args:
        d: Date to format.
        fmt: Format string (DD.MM.YYYY or YYYY-MM-DD).

    Returns:
        Formatted date string or empty string.
    """
    if d is None:
        return ""
    if fmt == "DD.MM.YYYY":
        return d.strftime("%d.%m.%Y")
    return d.strftime("%Y-%m-%d")


def format_serbian_number(
    value: Decimal | float | None,
    decimal_separator: str = ",",
) -> str:
    """Format a number using Serbian convention (45.000,00).

    Args:
        value: Decimal or float value.
        decimal_separator: ',' for Serbian, '.' for international.

    Returns:
        Formatted number string.
    """
    if value is None:
        return ""
    formatted = f"{float(value):,.2f}"
    if decimal_separator == ",":
        # 45,000.00 -> 45.000,00
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def extract_invoice_row(
    inv: Invoice,
    date_format: str = "DD.MM.YYYY",
    decimal_separator: str = ",",
) -> dict:
    """Extract a flat dict of export values from an Invoice.

    Args:
        inv: Invoice model instance.
        date_format: Date format string.
        decimal_separator: Decimal separator for number formatting.

    Returns:
        Dict with string keys matching INVOICE_HEADERS_SR keys.
    """
    seller = inv.seller if isinstance(inv.seller, dict) else {}
    buyer = inv.buyer if isinstance(inv.buyer, dict) else {}
    return {
        "invoice_number": inv.invoice_number or "",
        "invoice_date": format_serbian_date(inv.invoice_date, date_format),
        "due_date": format_serbian_date(inv.due_date, date_format),
        "seller_name": seller.get("name", ""),
        "seller_pib": seller.get("pib", ""),
        "seller_address": seller.get("address", ""),
        "seller_city": seller.get("city", ""),
        "buyer_name": buyer.get("name", ""),
        "buyer_pib": buyer.get("pib", ""),
        "subtotal": format_serbian_number(inv.subtotal, decimal_separator),
        "tax_rate": format_serbian_number(inv.tax_rate, decimal_separator),
        "tax_amount": format_serbian_number(inv.tax_amount, decimal_separator),
        "total_amount": format_serbian_number(inv.total_amount, decimal_separator),
        "currency": inv.currency or "RSD",
        "status": STATUS_LABELS_SR.get(inv.status, inv.status or ""),
        "confidence_score": format_serbian_number(inv.confidence_score, decimal_separator),
    }


def extract_accounting_row(
    inv: Invoice,
    decimal_separator: str = ",",
) -> dict | None:
    """Extract accounting intent data for export.

    Args:
        inv: Invoice with accounting_intent relationship loaded.
        decimal_separator: Decimal separator for number formatting.

    Returns:
        Dict with accounting data or None if no intent exists.
    """
    intent = inv.accounting_intent
    if intent is None:
        return None

    konta = intent.suggested_konta or {}
    debit_entries = konta.get("debit", [])
    credit_entries = konta.get("credit", [])

    debit_str = "; ".join(f"{e.get('konto', '')} - {e.get('name', '')}" for e in debit_entries)
    credit_str = "; ".join(f"{e.get('konto', '')} - {e.get('name', '')}" for e in credit_entries)

    return {
        "invoice_number": inv.invoice_number or "",
        "document_type": intent.document_type,
        "transaction_type": intent.transaction_type,
        "vat_treatment": intent.vat_treatment,
        "is_deductible": "Da" if intent.is_deductible else "Ne",
        "confidence": format_serbian_number(intent.confidence, decimal_separator),
        "requires_review": "Da" if intent.requires_review else "Ne",
        "debit_konta": debit_str,
        "credit_konta": credit_str,
    }


def apply_template(
    row_data: dict,
    template_fields: list[dict],
) -> OrderedDict:
    """Filter and reorder row data according to template field config.

    Takes the full row dict from extract_invoice_row() and returns only
    the fields specified in the template, in the template's order,
    with the template's custom labels as keys.

    Args:
        row_data: Full dict from extract_invoice_row() (keyed by field key).
        template_fields: List of {key, label, order} dicts from a template.

    Returns:
        OrderedDict with only the selected fields, using custom labels as keys.
    """
    sorted_fields = sorted(template_fields, key=lambda f: f["order"])
    result = OrderedDict()
    for field in sorted_fields:
        key = field["key"]
        label = field["label"]
        result[label] = row_data.get(key, "")
    return result
