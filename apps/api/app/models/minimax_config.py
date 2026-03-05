"""MiniMax integration configuration model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MiniMaxConfig(Base, UUIDMixin, TimestampMixin):
    """Per-organization MiniMax API credentials and settings.

    Stores encrypted OAuth2 credentials for the MiniMax accounting
    software integration. Each organization has at most one config.
    """

    __tablename__ = "minimax_configs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # OAuth2 credentials
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    # MiniMax organization ID (numeric, from MiniMax system)
    minimax_org_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", backref="minimax_config")
