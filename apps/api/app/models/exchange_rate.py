"""Exchange rate model for NBS (National Bank of Serbia) rates."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExchangeRate(Base, UUIDMixin, TimestampMixin):
    """Daily exchange rate from the National Bank of Serbia.

    Stores middle, buying, and selling rates for foreign currencies
    against RSD. Rates are fetched daily and cached in Redis.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("currency", "rate_date", name="uq_exchange_rate_currency_date"),
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Rates (middle rate is required, buying/selling optional)
    buying_rate: Mapped[Decimal | None] = mapped_column(Numeric(15, 6))
    middle_rate: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    selling_rate: Mapped[Decimal | None] = mapped_column(Numeric(15, 6))

    # Unit multiplier (e.g., 1 EUR = X RSD, but 100 JPY = X RSD)
    unit: Mapped[int] = mapped_column(Integer, default=1)

    # Metadata
    source: Mapped[str] = mapped_column(String(20), default="NBS")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
