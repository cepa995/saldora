"""Schemas for correction logging and analytics."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CorrectionLogResponse(BaseModel):
    """Single correction log entry."""

    id: UUID
    invoice_id: UUID
    organization_id: UUID
    user_id: UUID
    field_name: str
    original_value: str | None
    corrected_value: str
    model_confidence: float | None
    correction_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FieldErrorRate(BaseModel):
    """Per-field correction rate across all org invoices."""

    field_name: str
    correction_count: int
    invoice_count: int
    error_rate: float


class HighConfidenceError(BaseModel):
    """Fields where the model was confident (>90%) but wrong."""

    field_name: str
    count: int


class RepeatPattern(BaseModel):
    """Recurring original→corrected value pattern."""

    field_name: str
    original_value: str
    corrected_value: str
    occurrences: int


class CorrectionAnalyticsResponse(BaseModel):
    """Aggregated correction analytics for quality dashboard."""

    field_error_rates: list[FieldErrorRate]
    high_confidence_errors: list[HighConfidenceError]
    repeat_patterns: list[RepeatPattern]
