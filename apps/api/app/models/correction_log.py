"""
Correction log model.

Append-only table for quality monitoring (SRS Section 9.8).
Tracks every human correction to OCR-extracted data — which field
was wrong, what the model predicted vs what the user entered, and
how confident the model was.  Used for analytics, NOT model training.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class CorrectionLog(Base, UUIDMixin):
    """Immutable correction log entry."""

    __tablename__ = "correction_logs"

    # Context
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # What changed
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Quality metadata
    model_confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    correction_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # ocr_error, ner_error, layout_error, business_logic

    # When (append-only — no updated_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_correction_logs_invoice_id", "invoice_id"),
        Index("ix_correction_logs_organization_id", "organization_id"),
        Index("ix_correction_logs_field_name", "field_name"),
        Index("ix_correction_logs_created_at", "created_at"),
    )
