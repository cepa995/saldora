"""
Accounting intent generation pipeline (SRS Section 4.10).

5-step pipeline that classifies invoices, determines VAT treatment,
suggests konta, builds VAT breakdown, and flags for review.
Runs automatically when an invoice is verified.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, cast, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_intent import AccountingIntent
from app.models.invoice import Invoice
from app.models.organization import Organization

logger = logging.getLogger(__name__)

# EU member state VAT ID prefixes (2-letter country codes)
_EU_PREFIXES = {
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "EL",
    "ES",
    "FI",
    "FR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
}

# Non-deductible expense keyword patterns (Serbian)
_REPREZENTACIJA_KEYWORDS = [
    "reprezentacija",
    "ručak",
    "večera",
    "restoran",
    "kafić",
    "poklon",
    "ugošćavanje",
]
_GORIVO_KEYWORDS = ["gorivo", "benzin", "dizel", "nafta", "lpg"]
_ZABAVA_KEYWORDS = ["sponzorstvo", "donacija", "event", "zabava"]

# Keyword-to-konto mapping for expense classification
_EXPENSE_KONTA: dict[str, tuple[str, str]] = {
    "uslug": ("5330", "Troškovi usluga"),
    "servis": ("5330", "Troškovi usluga"),
    "konsult": ("5330", "Troškovi usluga"),
    "rob": ("5010", "Nabavna vrednost robe"),
    "materi": ("5010", "Nabavna vrednost robe"),
    "zakup": ("5350", "Troškovi zakupa"),
    "najam": ("5350", "Troškovi zakupa"),
    "rent": ("5350", "Troškovi zakupa"),
    "telekom": ("5210", "Troškovi telekomunikacija"),
    "telefon": ("5210", "Troškovi telekomunikacija"),
    "internet": ("5210", "Troškovi telekomunikacija"),
    "struji": ("5130", "Troškovi energije"),
    "energi": ("5130", "Troškovi energije"),
    "elektr": ("5130", "Troškovi energije"),
    "vod": ("5130", "Troškovi energije"),
    "greja": ("5130", "Troškovi energije"),
    "kancelar": ("5120", "Troškovi kancelarijskog materijala"),
    "štamp": ("5120", "Troškovi kancelarijskog materijala"),
    "papir": ("5120", "Troškovi kancelarijskog materijala"),
    "goriv": ("5131", "Troškovi goriva"),
    "benzin": ("5131", "Troškovi goriva"),
    "dizel": ("5131", "Troškovi goriva"),
    "reprezentaci": ("5191", "Troškovi reprezentacije"),
}

# High-value invoice threshold (RSD)
_HIGH_VALUE_THRESHOLD = Decimal("500000")


def _get_pib_from_party(party: dict | None) -> str | None:
    """Extract PIB from a seller/buyer JSON dict.

    Args:
        party: Seller or buyer JSON dict.

    Returns:
        PIB string or None.
    """
    if not party or not isinstance(party, dict):
        return None
    return party.get("pib")


def _is_serbian_pib(pib: str | None) -> bool:
    """Check if a PIB looks like a valid Serbian 9-digit PIB.

    Args:
        pib: PIB string to check.

    Returns:
        True if it's exactly 9 digits.
    """
    if not pib:
        return False
    cleaned = re.sub(r"[\s\-./]", "", pib.strip())
    return len(cleaned) == 9 and cleaned.isdigit()


def _get_eu_prefix(pib: str | None) -> str | None:
    """Extract EU VAT prefix if present.

    Args:
        pib: Tax ID string.

    Returns:
        2-letter EU country code or None.
    """
    if not pib or len(pib) < 3:
        return None
    prefix = pib[:2].upper()
    if prefix in _EU_PREFIXES:
        return prefix
    return None


def _text_contains_any(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the given keywords (case-insensitive).

    Args:
        text: Text to search.
        keywords: Keywords to look for.

    Returns:
        True if any keyword found.
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _collect_searchable_text(invoice: Invoice) -> str:
    """Combine invoice text sources for keyword scanning.

    Args:
        invoice: Invoice model instance.

    Returns:
        Combined lowercase text from invoice fields.
    """
    parts: list[str] = []
    if invoice.raw_ocr_text:
        parts.append(invoice.raw_ocr_text)
    if invoice.invoice_number:
        parts.append(invoice.invoice_number)
    if invoice.line_items and isinstance(invoice.line_items, list):
        for item in invoice.line_items:
            if isinstance(item, dict) and item.get("description"):
                parts.append(item["description"])
    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# Step 1: Document Classification
# ---------------------------------------------------------------------------


def classify_document(invoice: Invoice, organization_pib: str | None) -> tuple[str, Decimal]:
    """Classify document type based on org PIB and invoice content.

    Compares seller/buyer PIB to the organization's PIB to determine
    if this is an input or output invoice. Scans text for credit note,
    debit note, advance, and proforma keywords.

    Args:
        invoice: Invoice model instance.
        organization_pib: Organization's PIB (may be None).

    Returns:
        Tuple of (document_type, confidence).
    """
    seller_pib = _get_pib_from_party(invoice.seller)
    buyer_pib = _get_pib_from_party(invoice.buyer)
    text = _collect_searchable_text(invoice)

    # Determine base direction: INPUT vs OUTPUT
    is_input = True
    direction_confidence = Decimal("0.60")

    if organization_pib:
        org_pib_clean = re.sub(r"[\s\-./]", "", organization_pib.strip())
        seller_clean = re.sub(r"[\s\-./]", "", seller_pib.strip()) if seller_pib else ""
        buyer_clean = re.sub(r"[\s\-./]", "", buyer_pib.strip()) if buyer_pib else ""

        if buyer_clean == org_pib_clean:
            is_input = True
            direction_confidence = Decimal("0.95")
        elif seller_clean == org_pib_clean:
            is_input = False
            direction_confidence = Decimal("0.95")

    # Detect special document types via keywords
    credit_keywords = ["odobrenje", "storno", "knjižno odobrenje"]
    debit_keywords = ["zaduženje", "knjižno zaduženje"]
    advance_keywords = ["avansna", "avans"]
    proforma_keywords = ["profaktura", "proforma"]

    if _text_contains_any(text, credit_keywords):
        doc_type = "CREDIT_NOTE_IN" if is_input else "CREDIT_NOTE_OUT"
        return doc_type, direction_confidence * Decimal("0.90")

    if _text_contains_any(text, debit_keywords):
        doc_type = "DEBIT_NOTE_IN" if is_input else "DEBIT_NOTE_OUT"
        return doc_type, direction_confidence * Decimal("0.90")

    if _text_contains_any(text, advance_keywords):
        return "ADVANCE_INVOICE", direction_confidence * Decimal("0.85")

    if _text_contains_any(text, proforma_keywords):
        return "PROFORMA", direction_confidence * Decimal("0.85")

    doc_type = "INPUT_INVOICE" if is_input else "OUTPUT_INVOICE"
    return doc_type, direction_confidence


# ---------------------------------------------------------------------------
# Step 2: Transaction Type Detection
# ---------------------------------------------------------------------------


def detect_transaction_type(invoice: Invoice, document_type: str) -> tuple[str, Decimal]:
    """Detect transaction type based on counterparty PIB.

    Examines the counterparty (seller for INPUT, buyer for OUTPUT)
    to determine if the transaction is domestic, EU, or non-EU.

    Args:
        invoice: Invoice model instance.
        document_type: Document type from step 1.

    Returns:
        Tuple of (transaction_type, confidence).
    """
    is_input = document_type in (
        "INPUT_INVOICE",
        "CREDIT_NOTE_IN",
        "DEBIT_NOTE_IN",
    )

    # Counterparty is the other party
    if is_input:
        counterparty_pib = _get_pib_from_party(invoice.seller)
    else:
        counterparty_pib = _get_pib_from_party(invoice.buyer)

    text = _collect_searchable_text(invoice)

    # Check for reverse charge keywords
    if _text_contains_any(text, ["obrnuta naplata", "reverse charge"]):
        return "REVERSE_CHARGE", Decimal("0.90")

    if not counterparty_pib:
        return "DOMESTIC", Decimal("0.60")

    # Check if seller and buyer are the same entity (internal)
    seller_pib = _get_pib_from_party(invoice.seller)
    buyer_pib = _get_pib_from_party(invoice.buyer)
    if seller_pib and buyer_pib:
        s_clean = re.sub(r"[\s\-./]", "", seller_pib.strip())
        b_clean = re.sub(r"[\s\-./]", "", buyer_pib.strip())
        if s_clean == b_clean:
            return "INTERNAL", Decimal("0.95")

    # Check counterparty PIB format
    if _is_serbian_pib(counterparty_pib):
        return "DOMESTIC", Decimal("0.95")

    eu_prefix = _get_eu_prefix(counterparty_pib)
    if eu_prefix:
        return "FOREIGN_EU", Decimal("0.90")

    # Non-Serbian, non-EU
    return "FOREIGN_NON_EU", Decimal("0.85")


# ---------------------------------------------------------------------------
# Step 3: VAT Treatment
# ---------------------------------------------------------------------------


def determine_vat_treatment(
    invoice: Invoice,
    document_type: str,
    transaction_type: str,
) -> tuple[str, bool, Decimal]:
    """Determine VAT treatment and deductibility.

    For output invoices, checks tax rate. For input invoices, scans
    line items against non-deductible keyword patterns.

    Args:
        invoice: Invoice model instance.
        document_type: Document type from step 1.
        transaction_type: Transaction type from step 2.

    Returns:
        Tuple of (vat_treatment, is_deductible, confidence).
    """
    is_input = document_type in (
        "INPUT_INVOICE",
        "CREDIT_NOTE_IN",
        "DEBIT_NOTE_IN",
        "ADVANCE_INVOICE",
    )

    # Reverse charge
    if transaction_type == "REVERSE_CHARGE":
        if is_input:
            return "REVERSE_CHARGE_IN", True, Decimal("0.90")
        return "REVERSE_CHARGE_OUT", True, Decimal("0.90")

    # OUTPUT invoices — classify by tax rate
    if not is_input:
        rate = invoice.tax_rate
        if rate is None or rate == Decimal("0"):
            return "OUTPUT_EXEMPT", True, Decimal("0.85")
        if rate == Decimal("10") or rate == Decimal("10.00"):
            return "OUTPUT_REDUCED", True, Decimal("0.90")
        # Default: 20% standard rate
        return "OUTPUT_STANDARD", True, Decimal("0.90")

    # INPUT invoices — check deductibility by scanning line items
    text = _collect_searchable_text(invoice)

    # Check non-deductible categories
    if _text_contains_any(text, _ZABAVA_KEYWORDS):
        return "NON_DEDUCTIBLE", False, Decimal("0.80")

    if _text_contains_any(text, _GORIVO_KEYWORDS):
        return "NON_DEDUCTIBLE", False, Decimal("0.80")

    if _text_contains_any(text, _REPREZENTACIJA_KEYWORDS):
        return "DEDUCTIBLE_PARTIAL", True, Decimal("0.80")

    # Default: fully deductible
    return "DEDUCTIBLE_FULL", True, Decimal("0.85")


# ---------------------------------------------------------------------------
# Step 4: Konta Suggestion
# ---------------------------------------------------------------------------


def _match_expense_konto(text: str) -> tuple[str, str]:
    """Match expense konto from text keywords.

    Args:
        text: Combined searchable text.

    Returns:
        Tuple of (konto_code, konto_name).
    """
    text_lower = text.lower()
    for keyword, (code, name) in _EXPENSE_KONTA.items():
        if keyword in text_lower:
            return code, name
    # Default: general services
    return "5290", "Ostali troškovi"


def suggest_konta(
    invoice: Invoice,
    document_type: str,
    transaction_type: str,
    vat_treatment: str,
) -> tuple[dict, Decimal]:
    """Suggest debit and credit konta for the invoice.

    Follows SRS 4.10.3 structure with debit and credit arrays.
    Each entry has konto code, name, and amount.

    Args:
        invoice: Invoice model instance.
        document_type: From step 1.
        transaction_type: From step 2.
        vat_treatment: From step 3.

    Returns:
        Tuple of (suggested_konta dict, confidence).
    """
    total = invoice.total_amount or Decimal("0")
    tax = invoice.tax_amount or Decimal("0")
    base = invoice.subtotal or (total - tax)

    text = _collect_searchable_text(invoice)
    is_input = document_type in (
        "INPUT_INVOICE",
        "CREDIT_NOTE_IN",
        "DEBIT_NOTE_IN",
        "ADVANCE_INVOICE",
    )

    debit: list[dict] = []
    credit: list[dict] = []

    if is_input:
        # Expense konto (debit)
        expense_code, expense_name = _match_expense_konto(text)
        debit.append(
            {
                "konto": expense_code,
                "name": expense_name,
                "amount": str(base),
            }
        )

        # Input VAT (debit) — only if deductible
        if vat_treatment == "DEDUCTIBLE_FULL":
            debit.append(
                {
                    "konto": "2700",
                    "name": "PDV u primljenim fakturama",
                    "amount": str(tax),
                }
            )
        elif vat_treatment == "DEDUCTIBLE_PARTIAL":
            # 50% deductible (reprezentacija)
            deductible_tax = tax / 2
            non_deductible_tax = tax - deductible_tax
            debit.append(
                {
                    "konto": "2700",
                    "name": "PDV u primljenim fakturama",
                    "amount": str(deductible_tax),
                }
            )
            debit.append(
                {
                    "konto": "5799",
                    "name": "PDV koji se ne može odbiti",
                    "amount": str(non_deductible_tax),
                }
            )

        # Payable (credit)
        if transaction_type in ("FOREIGN_EU", "FOREIGN_NON_EU"):
            credit.append(
                {
                    "konto": "4340",
                    "name": "Dobavljači u inostranstvu",
                    "amount": str(total),
                }
            )
        else:
            credit.append(
                {
                    "konto": "4330",
                    "name": "Dobavljači u zemlji",
                    "amount": str(total),
                }
            )

    else:
        # OUTPUT invoice
        # Receivable (debit)
        debit.append(
            {
                "konto": "2040",
                "name": "Kupci u zemlji",
                "amount": str(total),
            }
        )

        # Revenue (credit)
        credit.append(
            {
                "konto": "6010",
                "name": "Prihodi od prodaje",
                "amount": str(base),
            }
        )

        # Output VAT (credit)
        if tax and tax > 0:
            credit.append(
                {
                    "konto": "4700",
                    "name": "Obaveze za PDV",
                    "amount": str(tax),
                }
            )

    suggested = {"debit": debit, "credit": credit}
    confidence = Decimal("0.80")

    return suggested, confidence


# ---------------------------------------------------------------------------
# VAT Breakdown Helper
# ---------------------------------------------------------------------------


def build_vat_breakdown(invoice: Invoice) -> dict:
    """Build VAT breakdown from invoice tax groups or single rate.

    Args:
        invoice: Invoice model instance.

    Returns:
        Dict with rate keys mapping to base and tax amounts.
    """
    breakdown: dict[str, dict[str, str]] = {}

    # Prefer tax_groups if available (multi-rate invoices)
    if invoice.tax_groups and isinstance(invoice.tax_groups, list):
        for group in invoice.tax_groups:
            if isinstance(group, dict):
                rate = group.get("rate", "0")
                base = group.get("base_amount", "0")
                tax = group.get("tax_amount", "0")
                key = f"rate_{rate}"
                breakdown[key] = {
                    "base": str(base),
                    "tax": str(tax),
                }
        return breakdown

    # Fall back to single tax_rate/tax_amount
    rate = invoice.tax_rate or Decimal("0")
    base = invoice.subtotal or Decimal("0")
    tax = invoice.tax_amount or Decimal("0")

    key = f"rate_{rate}"
    breakdown[key] = {
        "base": str(base),
        "tax": str(tax),
    }

    return breakdown


# ---------------------------------------------------------------------------
# PDV Book Mapping (SRS Section 4.10.4)
# ---------------------------------------------------------------------------

# Document types → book type
_KPR_DOC_TYPES = {
    "INPUT_INVOICE",
    "CREDIT_NOTE_IN",
    "DEBIT_NOTE_IN",
    "ADVANCE_INVOICE",
}
_KIR_DOC_TYPES = {
    "OUTPUT_INVOICE",
    "CREDIT_NOTE_OUT",
    "DEBIT_NOTE_OUT",
    "FINAL_INVOICE",
    "PROFORMA",
}


def _parse_rate(rate_key: str) -> Decimal:
    """Extract numeric rate from a vat_breakdown key like 'rate_20'.

    Args:
        rate_key: Key from vat_breakdown dict (e.g. 'rate_20', 'rate_10').

    Returns:
        Decimal rate value.
    """
    parts = rate_key.split("_", 1)
    try:
        return Decimal(parts[1]) if len(parts) > 1 else Decimal("0")
    except Exception:
        return Decimal("0")


def _build_pp_pdv_kpr(
    vat_treatment: str,
    vat_breakdown: dict,
) -> dict[str, str]:
    """Map VAT breakdown to PP-PDV fields for KPR (input invoices).

    Args:
        vat_treatment: VAT treatment classification.
        vat_breakdown: Dict with rate keys mapping to base/tax amounts.

    Returns:
        Dict of polje field names to string amounts.
    """
    fields: dict[str, str] = {}

    if vat_treatment == "NON_DEDUCTIBLE":
        return fields

    if vat_treatment == "REVERSE_CHARGE_IN":
        # Reverse charge: all amounts go to polje_8a
        total_base = Decimal("0")
        total_tax = Decimal("0")
        for _key, val in vat_breakdown.items():
            total_base += Decimal(val.get("base", "0"))
            total_tax += Decimal(val.get("tax", "0"))
        fields["polje_8a_1"] = str(total_base)
        fields["polje_8a_2"] = str(total_tax)
        return fields

    # DEDUCTIBLE_FULL or DEDUCTIBLE_PARTIAL
    deductible_ratio = Decimal("0.5") if vat_treatment == "DEDUCTIBLE_PARTIAL" else Decimal("1")

    for rate_key, val in vat_breakdown.items():
        rate = _parse_rate(rate_key)
        base = Decimal(val.get("base", "0")) * deductible_ratio
        tax = Decimal(val.get("tax", "0")) * deductible_ratio

        if rate >= 20:
            fields["polje_8_1"] = str(base)
            fields["polje_8_2"] = str(tax)
        elif rate >= 10:
            fields["polje_9_1"] = str(base)
            fields["polje_9_2"] = str(tax)
        # 0% rates are not recorded in pp_pdv_fields for KPR

    return fields


def _build_pp_pdv_kir(
    vat_treatment: str,
    vat_breakdown: dict,
) -> dict[str, str]:
    """Map VAT breakdown to PP-PDV fields for KIR (output invoices).

    Args:
        vat_treatment: VAT treatment classification.
        vat_breakdown: Dict with rate keys mapping to base/tax amounts.

    Returns:
        Dict of polje field names to string amounts.
    """
    fields: dict[str, str] = {}

    if vat_treatment == "REVERSE_CHARGE_OUT":
        total_base = Decimal("0")
        total_tax = Decimal("0")
        for _key, val in vat_breakdown.items():
            total_base += Decimal(val.get("base", "0"))
            total_tax += Decimal(val.get("tax", "0"))
        fields["polje_6a_1"] = str(total_base)
        fields["polje_6a_2"] = str(total_tax)
        return fields

    for rate_key, val in vat_breakdown.items():
        rate = _parse_rate(rate_key)
        base = val.get("base", "0")
        tax = val.get("tax", "0")

        if rate >= 20:
            fields["polje_3_1"] = str(base)
            fields["polje_3_2"] = str(tax)
        elif rate >= 10:
            fields["polje_4_1"] = str(base)
            fields["polje_4_2"] = str(tax)
        else:
            # Exempt — base only, no tax
            fields["polje_6"] = str(base)

    return fields


def generate_pdv_book_entries(
    invoice: Invoice,
    document_type: str,
    transaction_type: str,
    vat_treatment: str,
    vat_breakdown: dict,
    sequence: int,
) -> dict:
    """Generate PDV book entry for an invoice (SRS 4.10.4).

    Maps invoice data to KPR (received) or KIR (issued) book entries
    with PP-PDV field mappings for the Serbian VAT return form.

    Args:
        invoice: Invoice model instance.
        document_type: Classification from step 1.
        transaction_type: Transaction type from step 2.
        vat_treatment: VAT treatment from step 3.
        vat_breakdown: VAT breakdown by rate.
        sequence: Sequential entry number for this org/period.

    Returns:
        Dict with book_type, period, sequence, entry details, and pp_pdv_fields.
    """
    # Determine book type
    if document_type in _KPR_DOC_TYPES:
        book_type = "KPR"
    elif document_type in _KIR_DOC_TYPES:
        book_type = "KIR"
    else:
        book_type = "KPR"  # Default to received

    # Derive period from invoice date
    if invoice.invoice_date:
        period = invoice.invoice_date.strftime("%Y-%m")
    else:
        period = datetime.now(UTC).strftime("%Y-%m")

    # Extract counterparty info based on book type
    if book_type == "KPR":
        counterparty = invoice.seller or {}
        counterparty_pib = counterparty.get("pib", "") if isinstance(counterparty, dict) else ""
        counterparty_name = counterparty.get("name", "") if isinstance(counterparty, dict) else ""
    else:
        counterparty = invoice.buyer or {}
        counterparty_pib = counterparty.get("pib", "") if isinstance(counterparty, dict) else ""
        counterparty_name = counterparty.get("name", "") if isinstance(counterparty, dict) else ""

    # Extract per-rate amounts for the book entry
    base_20 = "0"
    vat_20 = "0"
    base_10 = "0"
    vat_10 = "0"

    for rate_key, val in vat_breakdown.items():
        rate = _parse_rate(rate_key)
        if rate >= 20:
            base_20 = val.get("base", "0")
            vat_20 = val.get("tax", "0")
        elif rate >= 10:
            base_10 = val.get("base", "0")
            vat_10 = val.get("tax", "0")

    # Build PP-PDV fields
    if book_type == "KPR":
        pp_pdv_fields = _build_pp_pdv_kpr(vat_treatment, vat_breakdown)
    else:
        pp_pdv_fields = _build_pp_pdv_kir(vat_treatment, vat_breakdown)

    entry_date = str(invoice.created_at.date()) if invoice.created_at else ""
    invoice_date_str = str(invoice.invoice_date) if invoice.invoice_date else ""

    return {
        "book_type": book_type,
        "period": period,
        "sequence": sequence,
        "entry_date": entry_date,
        "invoice_date": invoice_date_str,
        "invoice_number": invoice.invoice_number or "",
        "counterparty_pib": counterparty_pib or "",
        "counterparty_name": counterparty_name or "",
        "base_20": str(base_20),
        "vat_20": str(vat_20),
        "base_10": str(base_10),
        "vat_10": str(vat_10),
        "total": str(invoice.total_amount or "0"),
        "pp_pdv_fields": pp_pdv_fields,
    }


async def get_next_sequence(
    db: AsyncSession,
    organization_id: UUID,
    period: str,
) -> int:
    """Get the next sequential entry number for a PDV book period.

    Args:
        db: Database session.
        organization_id: Organization UUID.
        period: Period string (YYYY-MM).

    Returns:
        Next sequence number (1-based).
    """
    result = await db.execute(
        select(
            func.max(
                cast(
                    AccountingIntent.pdv_book_entries["sequence"].as_string(),
                    Integer,
                )
            )
        ).where(
            AccountingIntent.organization_id == organization_id,
            AccountingIntent.pdv_book_entries["period"].as_string() == period,
        )
    )
    max_seq = result.scalar()
    return (max_seq or 0) + 1


# ---------------------------------------------------------------------------
# Step 5: Review Flags
# ---------------------------------------------------------------------------


async def decide_review_flags(
    db: AsyncSession,
    invoice: Invoice,
    organization_id: UUID,
    confidence: Decimal,
    transaction_type: str,
    suggested_konta: dict,
) -> tuple[bool, list[str]]:
    """Decide whether the accounting intent needs manual review.

    Flags for review when confidence is low, transaction is foreign,
    a konto is new for the organization, or amount is high.

    Args:
        db: Database session.
        invoice: Invoice model instance.
        organization_id: Organization UUID.
        confidence: Overall pipeline confidence.
        transaction_type: From step 2.
        suggested_konta: From step 4.

    Returns:
        Tuple of (requires_review, list of reason strings).
    """
    reasons: list[str] = []

    # Low confidence
    if confidence < Decimal("0.80"):
        reasons.append("Nizak nivo pouzdanosti klasifikacije")

    # Non-domestic transaction
    if transaction_type not in ("DOMESTIC", "INTERNAL"):
        reasons.append(f"Inostrana transakcija: {transaction_type}")

    # High-value invoice
    total = invoice.total_amount or Decimal("0")
    if total > _HIGH_VALUE_THRESHOLD:
        reasons.append(f"Visok iznos fakture: {total} {invoice.currency or 'RSD'}")

    # Check for new konta (not seen before for this org)
    all_konta = set()
    for side in ("debit", "credit"):
        for entry in suggested_konta.get(side, []):
            if isinstance(entry, dict) and entry.get("konto"):
                all_konta.add(entry["konto"])

    if all_konta:
        existing_result = await db.execute(
            select(AccountingIntent.suggested_konta)
            .where(AccountingIntent.organization_id == organization_id)
            .limit(100)
        )
        existing_konta: set[str] = set()
        for (konta_json,) in existing_result:
            if isinstance(konta_json, dict):
                for side in ("debit", "credit"):
                    for entry in konta_json.get(side, []):
                        if isinstance(entry, dict) and entry.get("konto"):
                            existing_konta.add(entry["konto"])

        new_konta = all_konta - existing_konta
        if new_konta and existing_konta:
            reasons.append(f"Novo konto za organizaciju: {', '.join(sorted(new_konta))}")

    requires_review = len(reasons) > 0
    return requires_review, reasons


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def generate_accounting_intent(
    db: AsyncSession,
    invoice: Invoice,
    organization_id: UUID,
) -> AccountingIntent:
    """Generate accounting intent for an invoice.

    Runs the full 5-step pipeline: classify document, detect transaction
    type, determine VAT treatment, suggest konta, and decide review flags.
    Deletes any existing intent for re-verification scenarios.

    Args:
        db: Database session (caller manages commit).
        invoice: Invoice model instance.
        organization_id: Organization UUID.

    Returns:
        Created AccountingIntent instance (added to session, not committed).
    """
    # Fetch organization PIB
    org_result = await db.execute(
        select(Organization.pib).where(Organization.id == organization_id)
    )
    org_pib = org_result.scalar_one_or_none()

    # Step 1: Classify document
    document_type, doc_confidence = classify_document(invoice, org_pib)
    logger.info(
        "Invoice %s: document_type=%s (confidence=%.2f)",
        invoice.id,
        document_type,
        doc_confidence,
    )

    # Step 2: Detect transaction type
    transaction_type, txn_confidence = detect_transaction_type(invoice, document_type)
    logger.info(
        "Invoice %s: transaction_type=%s (confidence=%.2f)",
        invoice.id,
        transaction_type,
        txn_confidence,
    )

    # Step 3: Determine VAT treatment
    vat_treatment, is_deductible, vat_confidence = determine_vat_treatment(
        invoice, document_type, transaction_type
    )
    logger.info(
        "Invoice %s: vat_treatment=%s, deductible=%s (confidence=%.2f)",
        invoice.id,
        vat_treatment,
        is_deductible,
        vat_confidence,
    )

    # Step 4: Suggest konta
    suggested_konta_dict, konta_confidence = suggest_konta(
        invoice, document_type, transaction_type, vat_treatment
    )

    # Build VAT breakdown
    vat_breakdown = build_vat_breakdown(invoice)

    # Build PDV book entries (KPR/KIR)
    if invoice.invoice_date:
        period = invoice.invoice_date.strftime("%Y-%m")
    else:
        period = datetime.now(UTC).strftime("%Y-%m")
    sequence = await get_next_sequence(db, organization_id, period)
    pdv_book_entries = generate_pdv_book_entries(
        invoice, document_type, transaction_type, vat_treatment, vat_breakdown, sequence
    )

    # Calculate overall confidence (average of steps)
    overall_confidence = (doc_confidence + txn_confidence + vat_confidence + konta_confidence) / 4

    # Step 5: Review flags (async — queries DB)
    requires_review, review_reasons = await decide_review_flags(
        db,
        invoice,
        organization_id,
        overall_confidence,
        transaction_type,
        suggested_konta_dict,
    )

    logger.info(
        "Invoice %s: confidence=%.2f, requires_review=%s, reasons=%s",
        invoice.id,
        overall_confidence,
        requires_review,
        review_reasons,
    )

    # Delete existing intent for this invoice (re-verification case)
    await db.execute(delete(AccountingIntent).where(AccountingIntent.invoice_id == invoice.id))

    # Create new intent
    intent = AccountingIntent(
        invoice_id=invoice.id,
        organization_id=organization_id,
        document_type=document_type,
        transaction_type=transaction_type,
        vat_treatment=vat_treatment,
        is_deductible=is_deductible,
        vat_breakdown=vat_breakdown,
        suggested_konta=suggested_konta_dict,
        pdv_book_entries=pdv_book_entries,
        applied_rules=[],
        confidence=overall_confidence,
        requires_review=requires_review,
        review_reasons=review_reasons,
    )
    db.add(intent)

    return intent
