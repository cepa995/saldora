"""
Organization model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.user import User


class Organization(Base, UUIDMixin, TimestampMixin):
    """
    An organization (company/team) that owns invoices.

    Every user belongs to exactly one organization.
    Every invoice belongs to exactly one organization.
    This is the core multi-tenancy boundary.
    """

    __tablename__ = "organizations"
    __table_args__ = (Index("idx_organizations_slug", "slug", unique=True),)

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    pib: Mapped[str | None] = mapped_column(String(20))
    billing_email: Mapped[str | None] = mapped_column(String(255))
    payment_provider_customer_id: Mapped[str | None] = mapped_column(String(255))
    payment_provider_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(50), default="free")
    settings: Mapped[dict] = mapped_column(JSONB, server_default="{}", default=dict)

    # Relationships
    members: Mapped[list[User]] = relationship(back_populates="organization")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="organization")
