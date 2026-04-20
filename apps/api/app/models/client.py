"""
Client model — a company/entity managed by an agency organization.

Agencies manage invoices for multiple client companies. Each client
has their own PIB, contact info, and associated invoices.
Agency plan only (gated via Feature.CLIENT_MANAGEMENT).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.invoice import Invoice
    from app.models.organization import Organization


class Client(Base, UUIDMixin, TimestampMixin):
    """A client company managed by an agency organization.

    Agencies process invoices on behalf of their clients. Each client
    has a unique PIB within the organization, enabling auto-assignment
    of invoices based on PIB matching from OCR extraction.
    """

    __tablename__ = "clients"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )

    # Core identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pib: Mapped[str] = mapped_column(String(20), nullable=False)
    mb: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Client classification: vat_payer | pausalac | foreign_entity | non_profit
    client_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="vat_payer",
        default="vat_payer",
    )

    # Contact details
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Paušal-only fields (nullable; required at invoice-issuance time)
    bank_account: Mapped[str | None] = mapped_column(String(40), nullable=True)
    activity_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship()
    invoices: Mapped[list[Invoice]] = relationship(back_populates="client")
    customers: Mapped[list[Customer]] = relationship(
        back_populates="client", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "pib", name="uq_client_pib_per_org"),
        CheckConstraint(
            "client_type IN ('vat_payer', 'pausalac', 'foreign_entity', 'non_profit')",
            name="ck_clients_client_type",
        ),
        Index("ix_clients_org_id", "organization_id"),
        Index("ix_clients_pib", "pib"),
        Index(
            "ix_clients_org_active",
            "organization_id",
            "is_active",
        ),
        Index("ix_clients_org_type", "organization_id", "client_type"),
    )
