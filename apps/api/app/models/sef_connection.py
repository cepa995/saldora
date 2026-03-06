"""SEF connection configuration model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SefConnection(Base, UUIDMixin, TimestampMixin):
    """Per-organization SEF (eFaktura) API credentials and sync state.

    Stores encrypted API key or certificate path for connecting to the
    Serbian Electronic Invoicing System. Each organization has at most
    one SEF connection.
    """

    __tablename__ = "sef_connections"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Connection settings
    environment: Mapped[str] = mapped_column(String(20), default="production", nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pib: Mapped[str] = mapped_column(String(20), nullable=False)

    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Statistics
    total_invoices_synced: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    organization = relationship("Organization", backref="sef_connection")
