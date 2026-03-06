"""Extract structured invoice fields using Claude (Anthropic API)."""

import json
import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation

import anthropic

from fakturaai_ml.types import (
    CompanyData,
    ExtractedInvoice,
    LineItemData,
    TaxGroupData,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (  # noqa: E501
    "You are an expert invoice data extractor "
    "specializing in Serbian and Balkan invoices.\n\n"
    "Given raw OCR text from an invoice, extract all structured "
    "fields into the exact JSON schema below.\n\n"
    "RULES:\n"
    "- Return ONLY valid JSON, no markdown fences, no explanation.\n"
    "- CRITICAL: Extract ALL amounts exactly as printed on the "
    "invoice. NEVER compute or derive amounts. "
    "Read subtotal, tax_amount, and total_amount directly from "
    "the document text. "
    "Do NOT recalculate tax_amount from subtotal × rate. "
    "If the invoice has multiple sections (e.g. goods + services) "
    "each with their own subtotal and tax, "
    "sum the PRINTED values from each section. For example, if "
    'goods show "PDV: 19590.00" and services show '
    '"PDV: 11200.00", return tax_amount=30790.00 '
    "(the sum of printed tax values, NOT subtotal × rate).\n"
    '- "FAKTURISAO" or "FAKTURISALA" means the person/software '
    "that generated the invoice — this is NOT the seller name. "
    "The seller (prodavac) is typically at the top of the invoice "
    "with their address and PIB.\n"
    "- For amounts: normalize to plain decimal numbers "
    '(e.g. "6.597,00" → 6597.00, "1 234,56" → 1234.56). '
    "Serbian/Croatian format uses comma as decimal separator "
    "and period/space as thousands separator.\n"
    "- For dates: return as YYYY-MM-DD strings. "
    "Common formats: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD.\n"
    "- For tax_rate: return the numeric percentage "
    "(e.g. 20, 25, 10), not a decimal fraction.\n"
    "- For currency: detect from context "
    '(RSD, EUR, USD, HRK, BAM, etc.). Default to "RSD".\n'
    "- For PIB (Serbian tax ID): EXACTLY 9 digits, no more, no less. "
    "If a number is not exactly 9 digits, it is NOT a PIB.\n"
    "- FISCAL RECEIPTS (FISKALNI RAČUN / ФИСКАЛНИ РАЧУН): "
    "The seller PIB is the standalone 9-digit number printed near the "
    "top of the receipt, BEFORE the company name. Do NOT confuse it "
    "with store/branch numbers (e.g. '1036918-БС Нови Сад 16' — "
    "'1036918' is a store identifier, NOT a PIB).\n"
    "- BUYER ID on fiscal receipts: 'ИД купца: XX:NNNNNNNNN' — "
    "the XX before the colon is a buyer identification TYPE CODE "
    "(e.g. 10=PIB, 11=JMBG), NOT part of the ID itself. "
    "Extract ONLY the digits AFTER the colon as the buyer PIB "
    "(e.g. 'ИД купца: 10:111859782' → buyer PIB is '111859782').\n"
    "- For Croatian OIB: 11 digits. Extract what's present.\n"
    "- For MB (matični broj): typically 8 digits.\n"
    "- Extract ALL line items from tables, "
    "including HTML tables in OCR output.\n"
    "- For each line item, if the invoice prints a per-item PDV/tax "
    "amount (e.g. 'Iznos PDV-a', 'PDV' column), extract it into "
    "tax_amount. If the invoice does not show per-item tax, use null.\n"
    "- Extract EVERY separate PDV line into tax_groups. "
    "Each printed PDV row becomes one tax_group entry with rate, "
    "base_amount (osnovica), and tax_amount (PDV iznos). "
    "Do NOT merge rows that share the same rate. "
    "If goods show 'PDV 20%: 19590.00' and services show "
    "'PDV 20%: 11200.00', return TWO tax_groups both with "
    "rate=20, not one combined group. "
    "If only a single PDV line exists, include one entry. "
    "Leave tax_groups as empty array if no breakdown is visible.\n"
    "- If a field cannot be determined from the text, use null.\n"
    "- seller = the entity that issued the invoice "
    "(prodavac, dobavljač, isporučilac).\n"
    "- buyer = the entity that receives the invoice "
    "(kupac, primalac, naručilac)."
)

_JSON_SCHEMA = """\
{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "seller": {
    "pib": "string or null",
    "mb": "string or null",
    "name": "string or null",
    "address": "string or null",
    "city": "string or null",
    "postal_code": "string or null"
  },
  "buyer": {
    "pib": "string or null",
    "mb": "string or null",
    "name": "string or null",
    "address": "string or null",
    "city": "string or null",
    "postal_code": "string or null"
  },
  "subtotal": number_or_null,
  "tax_rate": number_or_null,
  "tax_amount": number_or_null,
  "total_amount": number_or_null,
  "currency": "string (ISO 4217 code, default RSD)",
  "line_items": [
    {
      "description": "string",
      "quantity": number_or_null,
      "unit_price": number_or_null,
      "total": number_or_null,
      "tax_rate": number_or_null,
      "tax_amount": number_or_null
    }
  ],
  "tax_groups": [
    {
      "rate": number,
      "base_amount": number,
      "tax_amount": number
    }
  ]
}"""


class LLMFieldExtractor:
    """Extract invoice fields using Claude (Anthropic API).

    Uses the Anthropic messages API to send raw OCR text and receive
    structured JSON with all invoice fields. Falls back gracefully
    if the API is unavailable or returns invalid data.

    Args:
        api_key: Anthropic API key. Reads ANTHROPIC_API_KEY env var if not provided.
        model: Claude model identifier (default: claude-haiku-4-5-20251001).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        """Initialize the LLM field extractor.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Claude model to use for extraction.
        """
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError("Anthropic API key required. Pass api_key or set ANTHROPIC_API_KEY.")
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model

    def extract(
        self,
        text: str,
        structured: dict | None = None,
    ) -> ExtractedInvoice:
        """Extract invoice fields from OCR text using Claude.

        Args:
            text: Raw OCR text from the invoice.
            structured: Optional structured OCR output (unused, kept for API compat).

        Returns:
            ExtractedInvoice with populated fields.

        Raises:
            Exception: If the API call fails or response cannot be parsed.
        """
        user_message = (
            f"<ocr_text>\n{text}\n</ocr_text>\n\n"
            f"Extract all invoice fields into this exact JSON schema:\n{_JSON_SCHEMA}"
        )

        logger.info("Calling Claude (%s) for field extraction...", self._model)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=0,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_output = response.content[0].text
        logger.info("Claude raw response:\n%s", raw_output)

        cleaned = _strip_markdown_fences(raw_output)
        data = json.loads(cleaned)
        invoice = self._to_extracted_invoice(data)
        invoice.raw_llm_output = cleaned
        return invoice

    def _to_extracted_invoice(self, data: dict) -> ExtractedInvoice:
        """Convert parsed JSON dict to ExtractedInvoice dataclass.

        Args:
            data: Parsed JSON dictionary from Claude response.

        Returns:
            ExtractedInvoice populated from the JSON data.
        """
        invoice = ExtractedInvoice()

        invoice.invoice_number = data.get("invoice_number")
        invoice.invoice_date = _parse_date(data.get("invoice_date"))
        invoice.due_date = _parse_date(data.get("due_date"))

        seller = data.get("seller") or {}
        invoice.seller = CompanyData(
            pib=seller.get("pib"),
            mb=seller.get("mb"),
            name=seller.get("name"),
            address=seller.get("address"),
            city=seller.get("city"),
            postal_code=seller.get("postal_code"),
        )

        buyer = data.get("buyer") or {}
        invoice.buyer = CompanyData(
            pib=buyer.get("pib"),
            mb=buyer.get("mb"),
            name=buyer.get("name"),
            address=buyer.get("address"),
            city=buyer.get("city"),
            postal_code=buyer.get("postal_code"),
        )

        invoice.subtotal = _parse_decimal(data.get("subtotal"))
        invoice.tax_rate = _parse_decimal(data.get("tax_rate"))
        invoice.tax_amount = _parse_decimal(data.get("tax_amount"))
        invoice.total_amount = _parse_decimal(data.get("total_amount"))
        invoice.currency = data.get("currency") or "RSD"

        for item in data.get("line_items") or []:
            invoice.line_items.append(
                LineItemData(
                    description=item.get("description", ""),
                    quantity=_parse_decimal(item.get("quantity")),
                    unit_price=_parse_decimal(item.get("unit_price")),
                    total=_parse_decimal(item.get("total")),
                    tax_rate=_parse_decimal(item.get("tax_rate")),
                    tax_amount=_parse_decimal(item.get("tax_amount")),
                )
            )

        for group in data.get("tax_groups") or []:
            rate = _parse_decimal(group.get("rate"))
            base = _parse_decimal(group.get("base_amount"))
            tax = _parse_decimal(group.get("tax_amount"))
            if rate is not None and base is not None and tax is not None:
                invoice.tax_groups.append(TaxGroupData(rate=rate, base_amount=base, tax_amount=tax))

        return invoice


def _parse_date(value: str | None) -> date | None:
    """Parse a YYYY-MM-DD date string, returning None on failure.

    Args:
        value: Date string in YYYY-MM-DD format, or None.

    Returns:
        Parsed date object, or None if parsing fails.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_decimal(value) -> Decimal | None:
    """Parse a numeric value to Decimal, returning None on failure.

    Args:
        value: Numeric value (int, float, str) or None.

    Returns:
        Decimal representation, or None if parsing fails.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM output.

    Handles responses wrapped in ```json ... ``` or ``` ... ```.

    Args:
        text: Raw LLM output that may contain markdown fences.

    Returns:
        The inner content with fences removed, or original text if no fences found.
    """
    import re

    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped
