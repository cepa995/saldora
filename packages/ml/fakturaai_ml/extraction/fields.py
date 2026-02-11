"""Extract structured fields from OCR text."""

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fakturaai_ml.types import ExtractedInvoice, LineItemData

logger = logging.getLogger(__name__)


class FieldExtractor:
    """
    Extract structured invoice fields from OCR text.

    Uses regex patterns and heuristics optimized for Serbian invoices.
    Supports both Cyrillic and Latin text.
    """

    # PIB patterns (Serbian Tax ID - 9 digits)
    PIB_PATTERNS = [
        r"ПИБ[:\s]*(\d{9})",  # Cyrillic
        r"PIB[:\s]*(\d{9})",  # Latin
        r"Порески\s+број[:\s]*(\d{9})",
        r"Poreski\s+broj[:\s]*(\d{9})",
    ]

    # MB patterns (Registration number - 8 digits)
    MB_PATTERNS = [
        r"МБ[:\s]*(\d{8})",
        r"MB[:\s]*(\d{8})",
        r"Матични\s+број[:\s]*(\d{8})",
        r"Matični\s+broj[:\s]*(\d{8})",
    ]

    # Invoice number patterns
    INVOICE_NUM_PATTERNS = [
        r"Фактура\s+бр(?:ој)?[.:\s]*([A-Za-z0-9\-/]+)",
        r"Faktura\s+br(?:oj)?[.:\s]*([A-Za-z0-9\-/]+)",
        r"Рачун\s+бр(?:ој)?[.:\s]*([A-Za-z0-9\-/]+)",
        r"Račun\s+br(?:oj)?[.:\s]*([A-Za-z0-9\-/]+)",
        r"Број\s+фактуре[:\s]*([A-Za-z0-9\-/]+)",
        r"Broj\s+fakture[:\s]*([A-Za-z0-9\-/]+)",
    ]

    # Date patterns
    DATE_PATTERNS = [
        r"(\d{1,2})[./](\d{1,2})[./](\d{4})",  # DD.MM.YYYY or DD/MM/YYYY
        r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})",  # YYYY-MM-DD
    ]

    # Amount patterns
    AMOUNT_PATTERNS = [
        r"([\d.,]+)\s*(?:RSD|дин|din|динара)?",
        r"(?:RSD|дин|din)\s*([\d.,]+)",
    ]

    # VAT rate patterns
    VAT_PATTERNS = [
        r"ПДВ\s*(\d{1,2})\s*%",
        r"PDV\s*(\d{1,2})\s*%",
        r"(\d{1,2})\s*%\s*ПДВ",
        r"(\d{1,2})\s*%\s*PDV",
    ]

    def __init__(self):
        """Initialize field extractor."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self._pib_re = [re.compile(p, re.IGNORECASE) for p in self.PIB_PATTERNS]
        self._mb_re = [re.compile(p, re.IGNORECASE) for p in self.MB_PATTERNS]
        self._invoice_re = [re.compile(p, re.IGNORECASE) for p in self.INVOICE_NUM_PATTERNS]
        self._date_re = [re.compile(p) for p in self.DATE_PATTERNS]
        self._amount_re = [re.compile(p, re.IGNORECASE) for p in self.AMOUNT_PATTERNS]
        self._vat_re = [re.compile(p, re.IGNORECASE) for p in self.VAT_PATTERNS]

    def extract(
        self,
        text: str,
        structured: dict[str, Any] | None = None,
    ) -> ExtractedInvoice:
        """
        Extract invoice fields from OCR text.

        Args:
            text: Raw OCR text
            structured: Optional structured output from OCR engine

        Returns:
            ExtractedInvoice with populated fields
        """
        invoice = ExtractedInvoice()

        # Extract PIBs (first two found are likely seller and buyer)
        pibs = self._extract_all_pibs(text)
        if len(pibs) >= 1:
            invoice.seller.pib = pibs[0]
        if len(pibs) >= 2:
            invoice.buyer.pib = pibs[1]

        # Extract MBs
        mbs = self._extract_all_mbs(text)
        if len(mbs) >= 1:
            invoice.seller.mb = mbs[0]
        if len(mbs) >= 2:
            invoice.buyer.mb = mbs[1]

        # Extract invoice number
        invoice.invoice_number = self._extract_invoice_number(text)

        # Extract dates
        dates = self._extract_all_dates(text)
        if dates:
            invoice.invoice_date = dates[0]
            if len(dates) >= 2:
                invoice.due_date = dates[1]

        # Extract amounts
        amounts = self._extract_amounts(text)
        if amounts:
            invoice.total_amount = amounts.get("total")
            invoice.subtotal = amounts.get("subtotal")
            invoice.tax_amount = amounts.get("tax")

        # Extract VAT rate
        invoice.tax_rate = self._extract_vat_rate(text)

        # Extract currency
        invoice.currency = self._extract_currency(text)

        # Try to extract company names
        invoice.seller.name = self._extract_company_name(text, "seller")
        invoice.buyer.name = self._extract_company_name(text, "buyer")

        # Extract line items if structured data available
        if structured:
            invoice.line_items = self._extract_line_items(structured)

        return invoice

    def _extract_all_pibs(self, text: str) -> list[str]:
        """Extract all PIB numbers from text."""
        pibs = []
        for pattern in self._pib_re:
            matches = pattern.findall(text)
            for match in matches:
                pib = match if isinstance(match, str) else match[0]
                if len(pib) == 9 and pib not in pibs:
                    pibs.append(pib)
        return pibs

    def _extract_all_mbs(self, text: str) -> list[str]:
        """Extract all MB numbers from text."""
        mbs = []
        for pattern in self._mb_re:
            matches = pattern.findall(text)
            for match in matches:
                mb = match if isinstance(match, str) else match[0]
                if len(mb) == 8 and mb not in mbs:
                    mbs.append(mb)
        return mbs

    def _extract_invoice_number(self, text: str) -> str | None:
        """Extract invoice number."""
        for pattern in self._invoice_re:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_all_dates(self, text: str) -> list[date]:
        """Extract all dates from text."""
        dates = []

        for pattern in self._date_re:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    if len(match[0]) == 4:  # YYYY-MM-DD format
                        d = date(int(match[0]), int(match[1]), int(match[2]))
                    else:  # DD.MM.YYYY format
                        d = date(int(match[2]), int(match[1]), int(match[0]))

                    # Sanity check: date should be reasonable
                    if 2000 <= d.year <= 2030:
                        dates.append(d)
                except (ValueError, IndexError):
                    continue

        return dates

    def _extract_amounts(self, text: str) -> dict[str, Decimal]:
        """Extract monetary amounts from text."""
        amounts: dict[str, Decimal] = {}

        # Look for labeled amounts
        total_patterns = [
            r"(?:Укупно|Ukupno|УКУПНО|UKUPNO|За\s+уплату|Za\s+uplatu)[:\s]*([\d.,]+)",
            r"(?:Износ|Iznos|ИЗНОС|IZNOS)[:\s]*([\d.,]+)",
        ]

        subtotal_patterns = [
            r"(?:Основица|Osnovica|ОСНОВИЦА|OSNOVICA)[:\s]*([\d.,]+)",
            r"(?:Без\s+ПДВ|Bez\s+PDV)[:\s]*([\d.,]+)",
        ]

        tax_patterns = [
            r"(?:ПДВ|PDV)[:\s]*([\d.,]+)",
            r"(?:Порез|Porez)[:\s]*([\d.,]+)",
        ]

        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amounts["total"] = self._parse_amount(match.group(1))
                break

        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amounts["subtotal"] = self._parse_amount(match.group(1))
                break

        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amounts["tax"] = self._parse_amount(match.group(1))
                break

        return amounts

    def _parse_amount(self, amount_str: str) -> Decimal | None:
        """Parse amount string to Decimal."""
        try:
            # Normalize: Serbian uses , as decimal separator
            # Remove thousand separators (. or space)
            normalized = amount_str.replace(" ", "").replace(".", "").replace(",", ".")
            return Decimal(normalized)
        except InvalidOperation:
            return None

    def _extract_vat_rate(self, text: str) -> Decimal | None:
        """Extract VAT rate from text."""
        for pattern in self._vat_re:
            match = pattern.search(text)
            if match:
                rate = int(match.group(1))
                if rate in [0, 10, 20]:  # Valid Serbian VAT rates
                    return Decimal(rate)
        return Decimal("20")  # Default to standard rate

    def _extract_currency(self, text: str) -> str:
        """Extract currency from text."""
        text_upper = text.upper()

        if "EUR" in text_upper or "€" in text:
            return "EUR"
        if "USD" in text_upper or "$" in text:
            return "USD"

        # Default to RSD for Serbian invoices
        return "RSD"

    def _extract_company_name(self, text: str, role: str) -> str | None:
        """Extract company name based on role (seller/buyer)."""
        # This is a simplified extraction - in production,
        # you'd use NER or more sophisticated patterns

        seller_markers = [
            "Продавац",
            "Prodavac",
            "ПРОДАВАЦ",
            "PRODAVAC",
            "Добављач",
            "Dobavljač",
            "Испоручилац",
        ]
        buyer_markers = [
            "Купац",
            "Kupac",
            "КУПАЦ",
            "KUPAC",
            "Прималац",
            "Primalac",
            "Наручилац",
        ]

        markers = seller_markers if role == "seller" else buyer_markers

        for marker in markers:
            pattern = rf"{marker}[:\s]*([^\n]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up common suffixes
                name = re.sub(r"^\s*[:-]\s*", "", name)
                if len(name) > 3:  # Minimum reasonable name length
                    return name

        return None

    def _extract_line_items(
        self,
        structured: dict[str, Any],
    ) -> list[LineItemData]:
        """Extract line items from structured OCR output."""
        items = []

        # Check for table data in structured output
        tables = structured.get("tables", structured.get("table", []))

        if not tables:
            return items

        # Parse table rows (format depends on OCR engine)
        # This is a simplified implementation
        for table in tables if isinstance(tables, list) else [tables]:
            rows = table.get("rows", table.get("data", []))
            for row in rows:
                try:
                    qty_str = str(row.get("quantity", row.get("kolicina", "")))
                    price_str = str(row.get("unit_price", row.get("cena", "")))
                    item = LineItemData(
                        description=str(row.get("description", row.get("opis", ""))),
                        quantity=self._parse_amount(qty_str),
                        unit_price=self._parse_amount(price_str),
                        total=self._parse_amount(str(row.get("total", row.get("iznos", "")))),
                    )
                    if item.description:
                        items.append(item)
                except Exception:
                    continue

        return items
