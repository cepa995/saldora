"""Confidence score calculation for extracted fields."""

import logging
from typing import Any

from fakturaai_ml.ocr.base import OCRResult
from fakturaai_ml.types import ExtractedInvoice, FieldConfidence

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Calculate confidence scores for extracted invoice fields.

    Combines multiple signals:
    - OCR engine confidence
    - Field validation success
    - Pattern matching strength
    - Cross-field consistency
    """

    # Weights for overall confidence calculation
    WEIGHTS = {
        "ocr_confidence": 0.40,
        "field_validation": 0.30,
        "pattern_strength": 0.20,
        "cross_validation": 0.10,
    }

    # Field importance for overall score
    FIELD_WEIGHTS = {
        "seller_pib": 1.0,
        "buyer_pib": 0.9,
        "invoice_number": 0.8,
        "invoice_date": 0.8,
        "total_amount": 1.0,
        "subtotal": 0.7,
        "tax_amount": 0.7,
        "tax_rate": 0.6,
        "seller_name": 0.5,
        "buyer_name": 0.5,
    }

    def __init__(self, confidence_threshold: float = 0.80):
        """
        Initialize confidence calculator.

        Args:
            confidence_threshold: Threshold below which fields need review
        """
        self.confidence_threshold = confidence_threshold

    def calculate(
        self,
        invoice: ExtractedInvoice,
        ocr_result: OCRResult,
    ) -> list[FieldConfidence]:
        """
        Calculate confidence for each extracted field.

        Args:
            invoice: Extracted invoice data
            ocr_result: OCR result with raw confidence

        Returns:
            List of FieldConfidence objects
        """
        confidences = []

        # Base OCR confidence
        base_confidence = ocr_result.confidence

        # Calculate per-field confidence
        if invoice.seller.pib:
            conf = self._calculate_pib_confidence(invoice.seller.pib, base_confidence)
            confidences.append(
                FieldConfidence(
                    field_name="seller_pib",
                    value=invoice.seller.pib,
                    confidence=conf,
                    source="ocr+validation",
                )
            )

        if invoice.buyer.pib:
            conf = self._calculate_pib_confidence(invoice.buyer.pib, base_confidence)
            confidences.append(
                FieldConfidence(
                    field_name="buyer_pib",
                    value=invoice.buyer.pib,
                    confidence=conf,
                    source="ocr+validation",
                )
            )

        if invoice.invoice_number:
            conf = base_confidence * 0.95  # Slightly lower - format varies
            confidences.append(
                FieldConfidence(
                    field_name="invoice_number",
                    value=invoice.invoice_number,
                    confidence=conf,
                    source="ocr",
                )
            )

        if invoice.invoice_date:
            conf = base_confidence * 0.90
            confidences.append(
                FieldConfidence(
                    field_name="invoice_date",
                    value=str(invoice.invoice_date),
                    confidence=conf,
                    source="ocr+validation",
                )
            )

        if invoice.total_amount:
            conf = self._calculate_amount_confidence(invoice, base_confidence)
            confidences.append(
                FieldConfidence(
                    field_name="total_amount",
                    value=str(invoice.total_amount),
                    confidence=conf,
                    source="ocr+math",
                )
            )

        if invoice.subtotal:
            conf = base_confidence * 0.85
            confidences.append(
                FieldConfidence(
                    field_name="subtotal",
                    value=str(invoice.subtotal),
                    confidence=conf,
                    source="ocr",
                )
            )

        if invoice.tax_amount:
            conf = base_confidence * 0.85
            confidences.append(
                FieldConfidence(
                    field_name="tax_amount",
                    value=str(invoice.tax_amount),
                    confidence=conf,
                    source="ocr",
                )
            )

        if invoice.tax_rate:
            conf = self._calculate_vat_confidence(invoice.tax_rate, base_confidence)
            confidences.append(
                FieldConfidence(
                    field_name="tax_rate",
                    value=str(invoice.tax_rate),
                    confidence=conf,
                    source="ocr+validation",
                )
            )

        if invoice.seller.name:
            conf = base_confidence * 0.75  # Names are harder to extract
            confidences.append(
                FieldConfidence(
                    field_name="seller_name",
                    value=invoice.seller.name,
                    confidence=conf,
                    source="ocr",
                )
            )

        if invoice.buyer.name:
            conf = base_confidence * 0.75
            confidences.append(
                FieldConfidence(
                    field_name="buyer_name",
                    value=invoice.buyer.name,
                    confidence=conf,
                    source="ocr",
                )
            )

        return confidences

    def calculate_overall(self, field_confidences: list[FieldConfidence]) -> float:
        """
        Calculate overall invoice confidence.

        Args:
            field_confidences: List of field confidence scores

        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        if not field_confidences:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for fc in field_confidences:
            weight = self.FIELD_WEIGHTS.get(fc.field_name, 0.5)
            weighted_sum += fc.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _calculate_pib_confidence(self, pib: str, base_confidence: float) -> float:
        """Calculate confidence for PIB field."""
        # Start with base confidence
        confidence = base_confidence

        # Boost if PIB passes format validation
        if len(pib) == 9 and pib.isdigit() and pib[0] != "0":
            confidence = min(1.0, confidence * 1.1)

            # Further boost if checksum validates
            if self._validate_pib_checksum(pib):
                confidence = min(1.0, confidence * 1.05)

        return confidence

    def _validate_pib_checksum(self, pib: str) -> bool:
        """Quick PIB checksum validation."""
        try:
            digits = [int(d) for d in pib]
            weights = [2, 3, 4, 5, 6, 7, 8, 9]
            weighted_sum = sum(d * w for d, w in zip(digits[:8], weights))
            remainder = weighted_sum % 11
            check_digit = 11 - remainder
            if check_digit >= 10:
                check_digit = 0
            return digits[8] == check_digit
        except (ValueError, IndexError):
            return False

    def _calculate_amount_confidence(
        self,
        invoice: ExtractedInvoice,
        base_confidence: float,
    ) -> float:
        """Calculate confidence for amount fields with cross-validation."""
        confidence = base_confidence

        # Boost if math checks out
        if invoice.subtotal and invoice.tax_amount and invoice.total_amount:
            expected = invoice.subtotal + invoice.tax_amount
            if abs(expected - invoice.total_amount) < 2:  # Within 2 RSD
                confidence = min(1.0, confidence * 1.1)

        return confidence

    def _calculate_vat_confidence(
        self,
        rate: Any,
        base_confidence: float,
    ) -> float:
        """Calculate confidence for VAT rate."""
        from decimal import Decimal

        confidence = base_confidence

        # High confidence for valid Serbian VAT rates
        try:
            rate_decimal = Decimal(str(rate))
            if rate_decimal in [Decimal("0"), Decimal("10"), Decimal("20")]:
                confidence = min(1.0, confidence * 1.15)
        except Exception:
            pass

        return confidence

    def get_fields_needing_review(
        self,
        field_confidences: list[FieldConfidence],
    ) -> list[FieldConfidence]:
        """Get list of fields that need manual review."""
        return [fc for fc in field_confidences if fc.confidence < self.confidence_threshold]
