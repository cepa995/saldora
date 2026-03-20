"""Type definitions for ML pipeline."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any


class ExtractionStatus(Enum):
    """Status of the extraction process."""

    SUCCESS = "success"
    PARTIAL = "partial"  # Some fields extracted with low confidence
    FAILED = "failed"


class WarningType(Enum):
    """Types of validation warnings."""

    PIB_INVALID_FORMAT = "pib_invalid_format"
    PIB_NOT_FOUND = "pib_not_found"
    PIB_INACTIVE = "pib_inactive"
    SAME_SELLER_BUYER = "same_seller_buyer"
    INVALID_VAT_RATE = "invalid_vat_rate"
    MATH_MISMATCH = "math_mismatch"
    CURRENCY_UNCLEAR = "currency_unclear"
    DATE_INVALID = "date_invalid"
    LOW_CONFIDENCE = "low_confidence"


@dataclass
class FieldConfidence:
    """Confidence information for an extracted field."""

    field_name: str
    value: Any
    confidence: float  # 0.0 to 1.0
    bounding_box: tuple[int, int, int, int] | None = None  # x1, y1, x2, y2
    source: str = "ocr"  # "ocr", "ner", "rule"
    needs_review: bool = False

    def __post_init__(self) -> None:
        """Set needs_review based on confidence threshold."""
        if self.confidence < 0.80:
            self.needs_review = True


@dataclass
class CompanyData:
    """Extracted company information."""

    pib: str | None = None
    mb: str | None = None  # Matični broj (registration number)
    name: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None

    # Confidence scores
    pib_confidence: float = 0.0
    name_confidence: float = 0.0


@dataclass
class LineItemData:
    """Extracted line item from invoice."""

    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    discount: Decimal | None = None
    tax_base: Decimal | None = None
    total: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    confidence: float = 0.0


@dataclass
class TaxGroupData:
    """A single tax rate group extracted from an invoice.

    Represents one section of tax breakdown (e.g. "goods at 20%").
    Values are extracted as printed on the document, never computed.
    """

    rate: Decimal
    base_amount: Decimal
    tax_amount: Decimal


@dataclass
class ValidationWarning:
    """Warning generated during validation."""

    warning_type: WarningType
    message: str
    field_name: str | None = None
    severity: str = "warning"  # "warning", "error", "info"
    blocking: bool = False  # If True, blocks export


@dataclass
class ExtractedInvoice:
    """Complete extracted invoice data."""

    # Core fields
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None

    # Parties
    seller: CompanyData = field(default_factory=CompanyData)
    buyer: CompanyData = field(default_factory=CompanyData)

    # Amounts
    subtotal: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str = "RSD"

    # Line items
    line_items: list[LineItemData] = field(default_factory=list)

    # Tax breakdown by rate (multi-rate invoices)
    tax_groups: list[TaxGroupData] = field(default_factory=list)

    # Raw OCR output
    raw_text: str = ""
    raw_structured: dict[str, Any] = field(default_factory=dict)

    # Raw LLM extraction output (JSON string for debugging)
    raw_llm_output: str | None = None


@dataclass
class ExtractionResult:
    """Complete result of invoice extraction."""

    status: ExtractionStatus
    invoice: ExtractedInvoice

    # Confidence scores
    overall_confidence: float = 0.0
    field_confidences: list[FieldConfidence] = field(default_factory=list)

    # Validation
    warnings: list[ValidationWarning] = field(default_factory=list)
    is_blocked: bool = False  # True if any blocking warning exists

    # Processing metadata
    processing_time_ms: int = 0
    ocr_engine: str = "unknown"
    model_version: str = "0.1.0"

    # Document info
    page_count: int = 1
    document_type: str = "invoice"

    def add_warning(self, warning: ValidationWarning) -> None:
        """Add a warning and update blocked status."""
        self.warnings.append(warning)
        if warning.blocking:
            self.is_blocked = True

    def get_warnings_by_severity(self, severity: str) -> list[ValidationWarning]:
        """Get warnings filtered by severity."""
        return [w for w in self.warnings if w.severity == severity]
