"""Per-client-per-year sequential invoice number counter.

One row per (client_id, year) pair. Atomic increment via
``SELECT ... FOR UPDATE`` in the issuance service guarantees
gap-free sequential numbering under concurrency.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class InvoiceCounter(Base, UUIDMixin, TimestampMixin):
    """Atomic counter for sequential invoice numbers per client per year."""

    __tablename__ = "invoice_counters"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("client_id", "year", name="uq_invoice_counter_client_year"),
        Index("ix_invoice_counters_client_year", "client_id", "year"),
    )
