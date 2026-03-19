"""
Deletion request model.

Tracks user requests for data erasure per ZZPL Article 30.
Profile data is anonymized while invoice data is retained
per the 10-year accounting law requirement.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class DeletionRequest(Base, UUIDMixin):
    """Data erasure request with processing workflow."""

    __tablename__ = "deletion_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    request_type: Mapped[str] = mapped_column(String(30), nullable=False, default="user_only")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    data_categories: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retained_categories: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_deletion_requests_user_id", "user_id"),
        Index("ix_deletion_requests_status", "status"),
        Index("ix_deletion_requests_org_id", "organization_id"),
    )
