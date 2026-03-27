"""Product catalog model for item normalization across suppliers.

Canonical product names with aliases enable accurate inventory tracking
and price comparison for restaurant/hospitality clients.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ProductCatalog(Base, UUIDMixin):
    """Canonical product entry with aliases for fuzzy matching."""

    __tablename__ = "product_catalog"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    unit_of_measure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    aliases: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    selling_price: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    default_margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_pc_org_id", "organization_id"),
        Index("ix_pc_org_name", "organization_id", "canonical_name", unique=True),
        Index("ix_pc_category", "category"),
    )
