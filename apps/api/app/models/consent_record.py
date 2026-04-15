"""
Consent record model.

Append-only table tracking user consent per type (ZZPL compliance).
Each grant or revocation creates a new row for a full audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ConsentRecord(Base, UUIDMixin):
    """Immutable consent tracking entry."""

    __tablename__ = "consent_records"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    granted: Mapped[bool] = mapped_column(nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_text_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_consent_records_org_id", "organization_id"),
        Index("ix_consent_records_user_id", "user_id"),
        Index("ix_consent_records_type", "consent_type"),
    )
