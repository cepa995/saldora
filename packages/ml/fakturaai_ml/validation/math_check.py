"""Mathematical validation for invoice calculations."""

import logging
from decimal import Decimal

from fakturaai_ml.types import ExtractedInvoice, ValidationWarning, WarningType

logger = logging.getLogger(__name__)


class MathValidator:
    """
    Validate mathematical correctness of invoice calculations.

    Checks:
    - Line items sum to subtotal
    - Tax calculation is correct
    - Total = Subtotal + Tax
    - Line item math (quantity * unit_price = total)
    """

    # Tolerance rules from SRS (4.9.5)
    TOLERANCE_RULES = [
        (Decimal("10000"), Decimal("1")),  # 0-10,000 RSD: ±1 RSD
        (Decimal("100000"), Decimal("5")),  # 10,001-100,000: ±5 RSD
        (Decimal("1000000"), Decimal("10")),  # 100,001-1,000,000: ±10 RSD
        (Decimal("999999999"), Decimal("50")),  # >1,000,000: ±50 RSD
    ]

    def __init__(self):
        """Initialize math validator."""
        self._warnings: list[ValidationWarning] = []

    def validate(self, invoice: ExtractedInvoice) -> bool:
        """
        Validate all mathematical aspects of invoice.

        Args:
            invoice: ExtractedInvoice to validate

        Returns:
            True if all checks pass, False otherwise
        """
        self._warnings = []
        all_valid = True

        # Check 1: Line items sum to subtotal
        if invoice.line_items and invoice.subtotal:
            if not self._validate_line_items_sum(invoice):
                all_valid = False

        # Check 2: Tax calculation
        if invoice.subtotal and invoice.tax_rate and invoice.tax_amount:
            if not self._validate_tax_calculation(invoice):
                all_valid = False

        # Check 3: Total = Subtotal + Tax
        if invoice.subtotal and invoice.tax_amount and invoice.total_amount:
            if not self._validate_total(invoice):
                all_valid = False

        # Check 4: Individual line item math
        if invoice.line_items:
            if not self._validate_line_item_math(invoice):
                all_valid = False

        return all_valid

    def _get_tolerance(self, amount: Decimal) -> Decimal:
        """Get tolerance for given amount based on rules."""
        abs_amount = abs(amount)
        for threshold, tolerance in self.TOLERANCE_RULES:
            if abs_amount <= threshold:
                return tolerance
        return Decimal("50")  # Default for very large amounts

    def _validate_line_items_sum(self, invoice: ExtractedInvoice) -> bool:
        """Validate that line items sum to subtotal."""
        calculated_subtotal = sum(item.total or Decimal("0") for item in invoice.line_items)

        if invoice.subtotal is None:
            return True

        difference = abs(calculated_subtotal - invoice.subtotal)
        tolerance = self._get_tolerance(invoice.subtotal)

        if difference > tolerance:
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.MATH_MISMATCH,
                    message=(
                        f"Stavke ({calculated_subtotal}) se ne slažu "
                        f"sa međuzbirom ({invoice.subtotal})"
                    ),
                    field_name="subtotal",
                    severity="warning",
                    blocking=False,
                )
            )
            return False

        return True

    def _validate_tax_calculation(self, invoice: ExtractedInvoice) -> bool:
        """Validate tax calculation."""
        if invoice.subtotal is None or invoice.tax_rate is None:
            return True

        expected_tax = invoice.subtotal * invoice.tax_rate / Decimal("100")
        difference = abs(expected_tax - (invoice.tax_amount or Decimal("0")))
        tolerance = self._get_tolerance(invoice.subtotal)

        if difference > tolerance:
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.MATH_MISMATCH,
                    message=(
                        f"Obračun PDV-a nije tačan. "
                        f"Očekivano: {expected_tax}, Dobijeno: {invoice.tax_amount}"
                    ),
                    field_name="tax_amount",
                    severity="warning",
                    blocking=False,
                )
            )
            return False

        return True

    def _validate_total(self, invoice: ExtractedInvoice) -> bool:
        """Validate total = subtotal + tax."""
        if invoice.subtotal is None or invoice.tax_amount is None:
            return True

        expected_total = invoice.subtotal + invoice.tax_amount
        actual_total = invoice.total_amount or Decimal("0")
        difference = abs(expected_total - actual_total)
        tolerance = self._get_tolerance(invoice.subtotal)

        if difference > tolerance:
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.MATH_MISMATCH,
                    message=(
                        f"Zbir nije tačan. Očekivano: {expected_total}, Dobijeno: {actual_total}"
                    ),
                    field_name="total_amount",
                    severity="warning",
                    blocking=False,
                )
            )
            return False

        return True

    def _validate_line_item_math(self, invoice: ExtractedInvoice) -> bool:
        """Validate individual line item calculations."""
        all_valid = True

        for i, item in enumerate(invoice.line_items):
            if item.quantity is None or item.unit_price is None or item.total is None:
                continue

            expected = item.quantity * item.unit_price
            difference = abs(expected - item.total)

            # Use 1 RSD tolerance per line item
            if difference > Decimal("1"):
                self._warnings.append(
                    ValidationWarning(
                        warning_type=WarningType.MATH_MISMATCH,
                        message=f"Greška u stavci {i + 1}: {item.description[:30]}",
                        field_name=f"line_item_{i}",
                        severity="warning",
                        blocking=False,
                    )
                )
                all_valid = False

        return all_valid

    def get_warnings(self) -> list[ValidationWarning]:
        """Get warnings from last validation."""
        return self._warnings.copy()

    def clear_warnings(self) -> None:
        """Clear accumulated warnings."""
        self._warnings = []


class VATRateValidator:
    """Validate VAT rates for Serbian invoices."""

    VALID_RATES = [Decimal("0"), Decimal("10"), Decimal("20")]

    def validate(self, rate: Decimal | None) -> tuple[bool, str | None]:
        """
        Validate VAT rate.

        Args:
            rate: VAT rate to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if rate is None:
            return False, "Stopa PDV-a nije detektovana"

        if rate not in self.VALID_RATES:
            return False, f"Nepoznata stopa PDV: {rate}%. Dozvoljene: 0%, 10%, 20%"

        return True, None
