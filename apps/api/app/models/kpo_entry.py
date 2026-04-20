"""KPO ledger entry (Knjiga o ostvarenom prometu).

One entry per issued paušal invoice (auto-populated), plus optional
manual entries for back-filling pre-Saldora history and storno entries
for corrections. Entries are effectively immutable after creation;
corrections are represented by new storno entries pointing at the
original via ``storno_of_id``.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.invoice import Invoice
    from app.models.organization import Organization


class KPOEntry(Base, UUIDMixin, TimestampMixin):
    """A single row in the KPO ledger (Knjiga o ostvarenom prometu)."""

    __tablename__ = "kpo_entries"

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
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    storno_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kpo_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_number: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)

    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_pib: Mapped[str | None] = mapped_column(String(20), nullable=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RSD")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    client: Mapped[Client] = relationship()
    organization: Mapped[Organization] = relationship()
    invoice: Mapped[Invoice | None] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "client_id", "year", "entry_number", name="uq_kpo_entry_client_year_number"
        ),
        Index("ix_kpo_entries_client_id", "client_id"),
        Index("ix_kpo_entries_org_id", "organization_id"),
        Index("ix_kpo_entries_invoice_id", "invoice_id"),
        Index("ix_kpo_entries_client_year", "client_id", "year"),
    )
