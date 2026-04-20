"""Customer model — buyer of invoices issued by a paušalac Client.

Customers are owned by a paušalac Client (``client_type='pausalac'``) and
represent the entities that buy the paušalac's goods/services. They are
distinct from ``Client`` because Clients belong to the agency/Organization
while Customers belong to a specific paušalac Client.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.organization import Organization


class Customer(Base, UUIDMixin, TimestampMixin):
    """A buyer of invoices issued by a paušalac Client."""

    __tablename__ = "customers"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_natural_person: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Legal identifiers — one of (pib+mb) or jmbg, depending on type
    pib: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mb: Mapped[str | None] = mapped_column(String(20), nullable=True)
    jmbg: Mapped[str | None] = mapped_column(String(13), nullable=True)

    # Contact + address
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="RS")
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    client: Mapped[Client] = relationship(back_populates="customers")
    organization: Mapped[Organization] = relationship()

    __table_args__ = (
        Index("ix_customers_client_id", "client_id"),
        Index("ix_customers_org_id", "organization_id"),
        Index("ix_customers_client_active", "client_id", "is_active"),
    )
