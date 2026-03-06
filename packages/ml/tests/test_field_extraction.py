"""Unit tests for field extraction, validation, and confidence scoring."""

from datetime import date
from decimal import Decimal

import pytest

from fakturaai_ml.extraction.fields import FieldExtractor
from fakturaai_ml.ocr.base import OCRResult
from fakturaai_ml.pipeline import InvoicePipeline, _snap_to_serbian_rate
from fakturaai_ml.postprocessing.confidence import ConfidenceCalculator
from fakturaai_ml.types import (
    CompanyData,
    ExtractedInvoice,
    FieldConfidence,
    LineItemData,
    WarningType,
)
from fakturaai_ml.validation.math_check import MathValidator, VATRateValidator
from fakturaai_ml.validation.pib import PIBValidator

# Valid PIBs with correct ISO 7064 Mod 11,10 checksums (pre-computed)
VALID_PIB_1 = "103867022"
VALID_PIB_2 = "205149838"
INVALID_PIB_CHECKSUM = "103867029"  # correct format, wrong check digit


# ===========================================================================
# FieldExtractor tests
# ===========================================================================


class TestExtractPIB:
    """Tests for PIB extraction from OCR text."""

    def test_extract_pib_cyrillic(self):
        extractor = FieldExtractor()
        invoice = extractor.extract(f"ПИБ: {VALID_PIB_1}")
        assert invoice.seller.pib == VALID_PIB_1

    def test_extract_pib_latin(self):
        extractor = FieldExtractor()
        invoice = extractor.extract(f"PIB: {VALID_PIB_2}")
        assert invoice.seller.pib == VALID_PIB_2

    def test_extract_two_pibs(self):
        extractor = FieldExtractor()
        text = f"Prodavac\nPIB: {VALID_PIB_1}\nKupac\nPIB: {VALID_PIB_2}"
        invoice = extractor.extract(text)
        assert invoice.seller.pib == VALID_PIB_1
        assert invoice.buyer.pib == VALID_PIB_2

    def test_extract_pib_poreski_broj(self):
        extractor = FieldExtractor()
        invoice = extractor.extract(f"Poreski broj: {VALID_PIB_1}")
        assert invoice.seller.pib == VALID_PIB_1


class TestExtractMB:
    """Tests for MB (matični broj) extraction."""

    def test_extract_mb_cyrillic(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("МБ: 12345678")
        assert invoice.seller.mb == "12345678"

    def test_extract_mb_latin(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("MB: 87654321")
        assert invoice.seller.mb == "87654321"


class TestExtractInvoiceNumber:
    """Tests for invoice number extraction."""

    def test_extract_invoice_number_latin(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Faktura br: 001/2025")
        assert invoice.invoice_number == "001/2025"

    def test_extract_invoice_number_cyrillic(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Фактура број: 001-2025")
        assert invoice.invoice_number == "001-2025"

    def test_extract_invoice_number_racun(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Račun br: R-123")
        assert invoice.invoice_number == "R-123"


class TestExtractDates:
    """Tests for date extraction."""

    def test_extract_date_dot_format(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Datum: 15.01.2025")
        assert invoice.invoice_date == date(2025, 1, 15)

    def test_extract_date_iso_format(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Datum: 2025-01-15")
        assert invoice.invoice_date == date(2025, 1, 15)

    def test_extract_two_dates(self):
        extractor = FieldExtractor()
        text = "Datum fakture: 15.01.2025\nRok plaćanja: 15.02.2025"
        invoice = extractor.extract(text)
        assert invoice.invoice_date == date(2025, 1, 15)
        assert invoice.due_date == date(2025, 2, 15)


class TestExtractAmounts:
    """Tests for amount extraction."""

    def test_extract_total_serbian_format(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Ukupno: 45.000,00")
        assert invoice.total_amount == Decimal("45000.00")

    def test_extract_subtotal_cyrillic(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Основица: 10.000,00")
        assert invoice.subtotal == Decimal("10000.00")

    def test_extract_tax_amount(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("PDV: 2.000,00")
        assert invoice.tax_amount == Decimal("2000.00")


class TestExtractVATRate:
    """Tests for VAT rate extraction."""

    def test_extract_vat_rate_20(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("PDV 20%")
        assert invoice.tax_rate == Decimal("20")

    def test_extract_vat_rate_cyrillic(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("ПДВ 10%")
        assert invoice.tax_rate == Decimal("10")

    def test_extract_vat_rate_default(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Nema pomena PDV-a")
        # Default VAT rate is 20%
        assert invoice.tax_rate == Decimal("20")


class TestExtractCurrency:
    """Tests for currency detection."""

    def test_extract_currency_rsd_default(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Ukupno: 5.000,00 dinara")
        assert invoice.currency == "RSD"

    def test_extract_currency_eur(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Total: 100.00 EUR")
        assert invoice.currency == "EUR"

    def test_extract_currency_usd(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Amount: $500.00 USD")
        assert invoice.currency == "USD"


class TestExtractCompanyName:
    """Tests for company name extraction."""

    def test_extract_seller_name(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Prodavac: Test DOO Beograd")
        assert invoice.seller.name == "Test DOO Beograd"

    def test_extract_buyer_name_cyrillic(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("Купац: Acme DOO Нови Сад")
        assert invoice.buyer.name == "Acme DOO Нови Сад"


class TestExtractLineItems:
    """Tests for line item extraction from structured data."""

    def test_extract_line_items_from_structured(self):
        extractor = FieldExtractor()
        structured = {
            "tables": [
                {
                    "rows": [
                        {
                            "description": "Usluga 1",
                            "quantity": "2",
                            "unit_price": "1.000,00",
                            "total": "2.000,00",
                        },
                        {
                            "description": "Usluga 2",
                            "quantity": "1",
                            "unit_price": "3.000,00",
                            "total": "3.000,00",
                        },
                    ]
                }
            ]
        }
        invoice = extractor.extract("", structured)
        assert len(invoice.line_items) == 2
        assert invoice.line_items[0].description == "Usluga 1"
        assert invoice.line_items[0].quantity == Decimal("2")

    def test_extract_line_items_empty_no_tables(self):
        extractor = FieldExtractor()
        invoice = extractor.extract("No structured data")
        assert invoice.line_items == []


class TestFullExtraction:
    """Integration tests with complete invoice text."""

    def test_full_extraction_latin_invoice(self):
        extractor = FieldExtractor()
        text = (
            f"Faktura br: F-2025/001\n"
            f"Datum: 15.01.2025\n"
            f"Rok plaćanja: 15.02.2025\n"
            f"\n"
            f"Prodavac: Test Company DOO\n"
            f"PIB: {VALID_PIB_1}\n"
            f"MB: 12345678\n"
            f"\n"
            f"Kupac: Buyer Company DOO\n"
            f"PIB: {VALID_PIB_2}\n"
            f"MB: 87654321\n"
            f"\n"
            f"Osnovica: 100.000,00\n"
            f"Porez: 20.000,00\n"
            f"Ukupno: 120.000,00 RSD\n"
        )
        invoice = extractor.extract(text)
        assert invoice.invoice_number == "F-2025/001"
        assert invoice.invoice_date == date(2025, 1, 15)
        assert invoice.due_date == date(2025, 2, 15)
        assert invoice.seller.pib == VALID_PIB_1
        assert invoice.seller.mb == "12345678"
        assert invoice.buyer.pib == VALID_PIB_2
        assert invoice.buyer.mb == "87654321"
        assert invoice.subtotal == Decimal("100000.00")
        assert invoice.tax_amount == Decimal("20000.00")
        assert invoice.total_amount == Decimal("120000.00")
        assert invoice.tax_rate == Decimal("20")
        assert invoice.currency == "RSD"

    def test_full_extraction_cyrillic_invoice(self):
        extractor = FieldExtractor()
        # Invoice number uses Latin chars (regex requires [A-Za-z0-9\-/])
        text = (
            f"Фактура број: INV-2025/002\n"
            f"Датум: 20.03.2025\n"
            f"\n"
            f"Продавац: Тест Компанија ДОО\n"
            f"ПИБ: {VALID_PIB_1}\n"
            f"МБ: 12345678\n"
            f"\n"
            f"Купац: Купац ДОО\n"
            f"ПИБ: {VALID_PIB_2}\n"
            f"\n"
            f"Основица: 50.000,00\n"
            f"Порез: 10.000,00\n"
            f"Укупно: 60.000,00\n"
        )
        invoice = extractor.extract(text)
        assert invoice.invoice_number == "INV-2025/002"
        assert invoice.invoice_date == date(2025, 3, 20)
        assert invoice.seller.pib == VALID_PIB_1
        assert invoice.buyer.pib == VALID_PIB_2
        assert invoice.subtotal == Decimal("50000.00")
        assert invoice.tax_amount == Decimal("10000.00")
        assert invoice.total_amount == Decimal("60000.00")


class TestParseAmount:
    """Tests for _parse_amount() helper."""

    def test_serbian_format(self):
        extractor = FieldExtractor()
        assert extractor._parse_amount("45.000,00") == Decimal("45000.00")

    def test_simple_decimal(self):
        extractor = FieldExtractor()
        assert extractor._parse_amount("1000,50") == Decimal("1000.50")

    def test_invalid_amount(self):
        extractor = FieldExtractor()
        assert extractor._parse_amount("abc") is None


# ===========================================================================
# PIBValidator tests
# ===========================================================================


class TestPIBValidator:
    """Tests for PIB format and checksum validation."""

    def test_valid_pib(self):
        validator = PIBValidator()
        assert validator.validate(VALID_PIB_1) is True
        assert len(validator.get_warnings()) == 0

    def test_invalid_pib_non_digits(self):
        validator = PIBValidator()
        assert validator.validate("12345abcd") is False
        warnings = validator.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].blocking is True

    def test_invalid_pib_wrong_length(self):
        validator = PIBValidator()
        assert validator.validate("12345") is False
        warnings = validator.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].warning_type == WarningType.PIB_INVALID_FORMAT

    def test_invalid_pib_starts_with_zero(self):
        validator = PIBValidator()
        assert validator.validate("012345678") is False
        warnings = validator.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].blocking is True

    def test_invalid_pib_checksum(self):
        validator = PIBValidator()
        assert validator.validate(INVALID_PIB_CHECKSUM) is False
        warnings = validator.get_warnings()
        assert len(warnings) == 1
        # Checksum failure is non-blocking (OCR might have misread)
        assert warnings[0].blocking is False

    def test_warnings_cleared_between_calls(self):
        validator = PIBValidator()
        validator.validate("bad")
        assert len(validator.get_warnings()) == 1
        validator.validate(VALID_PIB_1)
        assert len(validator.get_warnings()) == 0

    def test_empty_pib(self):
        validator = PIBValidator()
        assert validator.validate("") is False


# ===========================================================================
# MathValidator tests
# ===========================================================================


class TestMathValidatorTotal:
    """Tests for total = subtotal + tax validation."""

    def test_valid_total_calculation(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("100000"),
            tax_amount=Decimal("20000"),
            total_amount=Decimal("120000"),
            tax_rate=Decimal("20"),
        )
        assert validator.validate(invoice) is True
        assert len(validator.get_warnings()) == 0

    def test_invalid_total_mismatch(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("100000"),
            tax_amount=Decimal("20000"),
            total_amount=Decimal("999999"),
            tax_rate=Decimal("20"),
        )
        assert validator.validate(invoice) is False
        warnings = validator.get_warnings()
        assert any(w.warning_type == WarningType.MATH_MISMATCH for w in warnings)


class TestMathValidatorTax:
    """Tests for tax calculation validation."""

    def test_valid_tax_calculation(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("100000"),
            tax_rate=Decimal("20"),
            tax_amount=Decimal("20000"),
            total_amount=Decimal("120000"),
        )
        assert validator.validate(invoice) is True

    def test_invalid_total_does_not_equal_subtotal_plus_tax(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("100000"),
            tax_rate=Decimal("20"),
            tax_amount=Decimal("20000"),
            total_amount=Decimal("999999"),  # should be 120000
        )
        assert validator.validate(invoice) is False
        assert any(w.warning_type == WarningType.MATH_MISMATCH for w in validator.get_warnings())


class TestMathValidatorLineItems:
    """Tests for line item sum validation."""

    def test_line_items_sum_matches_subtotal(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("5000"),
            line_items=[
                LineItemData(
                    description="Item 1",
                    quantity=Decimal("2"),
                    unit_price=Decimal("1000"),
                    total=Decimal("2000"),
                ),
                LineItemData(
                    description="Item 2",
                    quantity=Decimal("1"),
                    unit_price=Decimal("3000"),
                    total=Decimal("3000"),
                ),
            ],
        )
        assert validator.validate(invoice) is True

    def test_line_items_sum_mismatch(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("99999"),
            line_items=[
                LineItemData(
                    description="Item 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100"),
                    total=Decimal("100"),
                ),
            ],
        )
        assert validator.validate(invoice) is False

    def test_line_items_vat_inclusive_matches_total(self):
        """Items priced with VAT sum to total_amount, not subtotal — valid."""
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("10482.58"),
            tax_amount=Decimal("2096.52"),
            total_amount=Decimal("12579.10"),
            tax_rate=Decimal("20"),
            line_items=[
                LineItemData(description="FILTER KABINE", total=Decimal("1639.50")),
                LineItemData(description="FILTER ULJA", total=Decimal("1111.50")),
                LineItemData(description="Usluga servisa", total=Decimal("9828.10")),
            ],
        )
        assert validator.validate(invoice) is True
        assert not any(w.field_name == "subtotal" for w in validator.get_warnings())

    def test_line_items_neither_subtotal_nor_total(self):
        """Items sum matches neither subtotal nor total — genuine mismatch."""
        validator = MathValidator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("10000"),
            total_amount=Decimal("12000"),
            line_items=[
                LineItemData(description="Item", total=Decimal("5000")),
            ],
        )
        assert validator.validate(invoice) is False
        assert any(w.field_name == "subtotal" for w in validator.get_warnings())

    def test_line_item_math_valid(self):
        validator = MathValidator()
        invoice = ExtractedInvoice(
            line_items=[
                LineItemData(
                    description="Product A",
                    quantity=Decimal("5"),
                    unit_price=Decimal("200"),
                    total=Decimal("1000"),
                ),
            ],
        )
        assert validator.validate(invoice) is True


class TestMathValidatorTolerance:
    """Tests for tolerance rules."""

    def test_tolerance_small_amount(self):
        validator = MathValidator()
        # Under 10,000 RSD → ±1 RSD tolerance
        assert validator._get_tolerance(Decimal("5000")) == Decimal("1")

    def test_tolerance_medium_amount(self):
        validator = MathValidator()
        # 10,001-100,000 → ±5 RSD
        assert validator._get_tolerance(Decimal("50000")) == Decimal("5")

    def test_tolerance_large_amount(self):
        validator = MathValidator()
        # 100,001-1,000,000 → ±10 RSD
        assert validator._get_tolerance(Decimal("500000")) == Decimal("10")

    def test_tolerance_very_large_amount(self):
        validator = MathValidator()
        # >1,000,000 → ±50 RSD
        assert validator._get_tolerance(Decimal("5000000")) == Decimal("50")


# ===========================================================================
# VATRateValidator tests
# ===========================================================================


class TestVATRateValidator:
    """Tests for VAT rate validation."""

    @pytest.mark.parametrize("rate", [Decimal("0"), Decimal("10"), Decimal("20")])
    def test_valid_rates(self, rate):
        validator = VATRateValidator()
        is_valid, msg = validator.validate(rate)
        assert is_valid is True
        assert msg is None

    def test_invalid_rate(self):
        validator = VATRateValidator()
        is_valid, msg = validator.validate(Decimal("15"))
        assert is_valid is False
        assert msg is not None

    def test_none_rate(self):
        validator = VATRateValidator()
        is_valid, msg = validator.validate(None)
        assert is_valid is False


# ===========================================================================
# ConfidenceCalculator tests
# ===========================================================================


def _make_ocr_result(confidence: float = 0.90) -> OCRResult:
    """Create an OCRResult with the given confidence."""
    return OCRResult(text="sample text", confidence=confidence, structured={})


class TestConfidenceCalculate:
    """Tests for per-field confidence calculation."""

    def test_calculate_returns_field_confidences(self):
        calculator = ConfidenceCalculator()
        invoice = ExtractedInvoice(
            seller=CompanyData(pib=VALID_PIB_1),
            invoice_number="F-001",
            total_amount=Decimal("10000"),
        )
        ocr = _make_ocr_result(0.90)
        confidences = calculator.calculate(invoice, ocr)
        assert len(confidences) >= 3
        field_names = [fc.field_name for fc in confidences]
        assert "seller_pib" in field_names
        assert "invoice_number" in field_names
        assert "total_amount" in field_names

    def test_pib_checksum_boosts_confidence(self):
        calculator = ConfidenceCalculator()
        base = 0.85
        # Valid PIB with correct checksum should boost confidence
        boosted = calculator._calculate_pib_confidence(VALID_PIB_1, base)
        assert boosted > base

    def test_pib_invalid_format_no_boost(self):
        calculator = ConfidenceCalculator()
        base = 0.85
        # Invalid format (too short) — no boost
        conf = calculator._calculate_pib_confidence("123", base)
        assert conf == base

    def test_amount_cross_validation_boosts(self):
        calculator = ConfidenceCalculator()
        invoice = ExtractedInvoice(
            subtotal=Decimal("10000"),
            tax_amount=Decimal("2000"),
            total_amount=Decimal("12000"),
        )
        base = 0.85
        boosted = calculator._calculate_amount_confidence(invoice, base)
        assert boosted > base

    def test_vat_valid_rate_boosts(self):
        calculator = ConfidenceCalculator()
        base = 0.85
        boosted = calculator._calculate_vat_confidence(Decimal("20"), base)
        assert boosted > base


class TestConfidenceOverall:
    """Tests for overall confidence calculation."""

    def test_overall_confidence_weighted(self):
        calculator = ConfidenceCalculator()
        field_confidences = [
            FieldConfidence(field_name="seller_pib", value="123456789", confidence=0.95),
            FieldConfidence(field_name="total_amount", value="10000", confidence=0.85),
        ]
        overall = calculator.calculate_overall(field_confidences)
        # Both have weight 1.0, so average = (0.95 + 0.85) / 2 = 0.90
        assert overall == pytest.approx(0.90, abs=0.01)

    def test_overall_empty_returns_zero(self):
        calculator = ConfidenceCalculator()
        assert calculator.calculate_overall([]) == 0.0

    def test_fields_needing_review(self):
        calculator = ConfidenceCalculator()
        fields = [
            FieldConfidence(field_name="seller_pib", value="123456789", confidence=0.95),
            FieldConfidence(field_name="buyer_name", value="Test", confidence=0.60),
        ]
        needs_review = calculator.get_fields_needing_review(fields)
        assert len(needs_review) == 1
        assert needs_review[0].field_name == "buyer_name"


# ===========================================================================
# Amount derivation tests (InvoicePipeline._derive_amounts)
# ===========================================================================


class TestDeriveAmounts:
    """Tests for _derive_amounts() — filling missing amount fields."""

    def _derive(self, invoice: ExtractedInvoice) -> None:
        """Call _derive_amounts on a pipeline instance."""
        pipeline = InvoicePipeline.__new__(InvoicePipeline)
        pipeline._derive_amounts(invoice)

    def test_subtotal_only_no_tax_fields(self):
        """subtotal=900000, no tax fields → total_amount = subtotal."""
        inv = ExtractedInvoice(subtotal=Decimal("900000"))
        self._derive(inv)
        assert inv.total_amount == Decimal("900000")

    def test_subtotal_with_zero_tax_rate(self):
        """subtotal=50000, tax_rate=0 → total_amount = subtotal."""
        inv = ExtractedInvoice(subtotal=Decimal("50000"), tax_rate=Decimal("0"))
        self._derive(inv)
        assert inv.total_amount == Decimal("50000")
        assert inv.tax_amount == Decimal("0")

    def test_subtotal_with_zero_tax_amount(self):
        """subtotal=50000, tax_amount=0 → total_amount = subtotal."""
        inv = ExtractedInvoice(subtotal=Decimal("50000"), tax_amount=Decimal("0"))
        self._derive(inv)
        assert inv.total_amount == Decimal("50000")

    def test_subtotal_plus_tax_amount(self):
        """subtotal=10000, tax_amount=2000 → total_amount = 12000."""
        inv = ExtractedInvoice(subtotal=Decimal("10000"), tax_amount=Decimal("2000"))
        self._derive(inv)
        assert inv.total_amount == Decimal("12000")

    def test_subtotal_plus_tax_rate(self):
        """subtotal=10000, tax_rate=20 → tax_amount=2000, total=12000."""
        inv = ExtractedInvoice(subtotal=Decimal("10000"), tax_rate=Decimal("20"))
        self._derive(inv)
        assert inv.tax_amount == Decimal("2000.00")
        assert inv.total_amount == Decimal("12000.00")

    def test_total_minus_tax_gives_subtotal(self):
        """total=12000, tax_amount=2000 → subtotal = 10000."""
        inv = ExtractedInvoice(total_amount=Decimal("12000"), tax_amount=Decimal("2000"))
        self._derive(inv)
        assert inv.subtotal == Decimal("10000")

    def test_total_with_zero_tax_gives_subtotal(self):
        """total=50000, tax_rate=0 → subtotal = 50000."""
        inv = ExtractedInvoice(total_amount=Decimal("50000"), tax_rate=Decimal("0"))
        self._derive(inv)
        assert inv.subtotal == Decimal("50000")

    def test_all_present_no_change(self):
        """All fields present → no modification."""
        inv = ExtractedInvoice(
            subtotal=Decimal("10000"),
            tax_rate=Decimal("20"),
            tax_amount=Decimal("2000"),
            total_amount=Decimal("12000"),
        )
        self._derive(inv)
        assert inv.subtotal == Decimal("10000")
        assert inv.total_amount == Decimal("12000")

    def test_nothing_present_no_change(self):
        """All fields None → no modification."""
        inv = ExtractedInvoice()
        self._derive(inv)
        assert inv.subtotal is None
        assert inv.total_amount is None

    def test_infer_tax_rate_from_subtotal_and_tax_amount(self):
        """subtotal=10482.58, tax_amount=2096.52 → tax_rate=20 (snapped)."""
        inv = ExtractedInvoice(
            subtotal=Decimal("10482.58"),
            tax_amount=Decimal("2096.52"),
            total_amount=Decimal("12579.10"),
        )
        self._derive(inv)
        assert inv.tax_rate == Decimal("20")

    def test_infer_tax_rate_10_percent(self):
        """subtotal=10000, tax_amount=1000 → tax_rate=10."""
        inv = ExtractedInvoice(
            subtotal=Decimal("10000"),
            tax_amount=Decimal("1000"),
            total_amount=Decimal("11000"),
        )
        self._derive(inv)
        assert inv.tax_rate == Decimal("10")

    def test_infer_tax_rate_no_snap_for_invalid(self):
        """subtotal=10000, tax_amount=1500 (15%) → no valid Serbian rate."""
        inv = ExtractedInvoice(
            subtotal=Decimal("10000"),
            tax_amount=Decimal("1500"),
            total_amount=Decimal("11500"),
        )
        self._derive(inv)
        assert inv.tax_rate is None

    def test_infer_tax_groups_when_empty(self):
        """Empty tax_groups + known amounts → single group inferred."""
        inv = ExtractedInvoice(
            subtotal=Decimal("10000"),
            tax_amount=Decimal("2000"),
            total_amount=Decimal("12000"),
            tax_rate=Decimal("20"),
        )
        self._derive(inv)
        assert len(inv.tax_groups) == 1
        assert inv.tax_groups[0].rate == Decimal("20")
        assert inv.tax_groups[0].base_amount == Decimal("10000")
        assert inv.tax_groups[0].tax_amount == Decimal("2000")

    def test_infer_tax_rate_then_groups(self):
        """Both tax_rate and tax_groups inferred in one pass."""
        inv = ExtractedInvoice(
            subtotal=Decimal("10000"),
            tax_amount=Decimal("2000"),
            total_amount=Decimal("12000"),
        )
        self._derive(inv)
        assert inv.tax_rate == Decimal("20")
        assert len(inv.tax_groups) == 1


# ===========================================================================
# _snap_to_serbian_rate tests
# ===========================================================================


class TestSnapToSerbianRate:
    """Tests for the _snap_to_serbian_rate helper."""

    def test_exact_20(self):
        assert _snap_to_serbian_rate(Decimal("20")) == Decimal("20")

    def test_exact_10(self):
        assert _snap_to_serbian_rate(Decimal("10")) == Decimal("10")

    def test_exact_0(self):
        assert _snap_to_serbian_rate(Decimal("0")) == Decimal("0")

    def test_close_to_20(self):
        assert _snap_to_serbian_rate(Decimal("19.98")) == Decimal("20")
        assert _snap_to_serbian_rate(Decimal("20.05")) == Decimal("20")

    def test_close_to_10(self):
        assert _snap_to_serbian_rate(Decimal("10.50")) == Decimal("10")

    def test_too_far_from_any_rate(self):
        assert _snap_to_serbian_rate(Decimal("15")) is None

    def test_boundary_within_1(self):
        assert _snap_to_serbian_rate(Decimal("21")) == Decimal("20")

    def test_boundary_beyond_1(self):
        assert _snap_to_serbian_rate(Decimal("21.01")) is None


# ===========================================================================
# PIB sanitization tests (InvoicePipeline._sanitize_pibs)
# ===========================================================================


class TestSanitizePIBs:
    """Tests for _sanitize_pibs() — fixing common LLM extraction errors."""

    def _sanitize(self, invoice: ExtractedInvoice) -> None:
        """Call _sanitize_pibs on a pipeline instance."""
        pipeline = InvoicePipeline.__new__(InvoicePipeline)
        pipeline._sanitize_pibs(invoice)

    def test_fiscal_receipt_buyer_id_prefix(self):
        """'10:111859782' → '111859782' (strip type-code prefix)."""
        inv = ExtractedInvoice(
            buyer=CompanyData(pib="10:111859782"),
        )
        self._sanitize(inv)
        assert inv.buyer.pib == "111859782"

    def test_fiscal_receipt_jmbg_prefix_not_9_digits(self):
        """'11:0101990710234' — not 9 digits after colon, kept as-is."""
        inv = ExtractedInvoice(
            buyer=CompanyData(pib="11:0101990710234"),
        )
        self._sanitize(inv)
        # Candidate after colon is not 9 digits → left unchanged for validation
        assert inv.buyer.pib == "11:0101990710234"

    def test_clean_pib_no_change(self):
        """Valid 9-digit PIB passes through unchanged."""
        inv = ExtractedInvoice(
            seller=CompanyData(pib=VALID_PIB_1),
        )
        self._sanitize(inv)
        assert inv.seller.pib == VALID_PIB_1

    def test_strips_ocr_noise(self):
        """Whitespace, dashes, dots stripped from PIB."""
        inv = ExtractedInvoice(
            seller=CompanyData(pib="103 867-022"),
        )
        self._sanitize(inv)
        assert inv.seller.pib == "103867022"

    def test_none_pib_no_error(self):
        """None PIB is skipped without error."""
        inv = ExtractedInvoice(
            seller=CompanyData(pib=None),
            buyer=CompanyData(pib=None),
        )
        self._sanitize(inv)
        assert inv.seller.pib is None
        assert inv.buyer.pib is None

    def test_empty_pib_no_error(self):
        """Empty string PIB is skipped without error."""
        inv = ExtractedInvoice(
            seller=CompanyData(pib=""),
        )
        self._sanitize(inv)
        assert inv.seller.pib == ""

    def test_both_seller_and_buyer_sanitized(self):
        """Both seller and buyer PIBs are sanitized."""
        inv = ExtractedInvoice(
            seller=CompanyData(pib="103.867.022"),
            buyer=CompanyData(pib="10:111859782"),
        )
        self._sanitize(inv)
        assert inv.seller.pib == "103867022"
        assert inv.buyer.pib == "111859782"
