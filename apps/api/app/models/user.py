"""
User model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class User(Base, UUIDMixin, TimestampMixin):
    """Application user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(
        String(20), default="viewer"
    )  # Possible choices: admin, manager, operator, viewer
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign keys
    organization_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )

    # Relationships
    organization: Mapped[Organization | None] = relationship(back_populates="members")
