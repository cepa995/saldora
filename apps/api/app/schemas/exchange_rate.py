"""Exchange rate schemas."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ExchangeRateResponse(BaseModel):
    """Single exchange rate entry."""

    id: UUID
    currency: str = Field(description="ISO 4217 currency code")
    rate_date: date
    buying_rate: Decimal | None = None
    middle_rate: Decimal
    selling_rate: Decimal | None = None
    unit: int = Field(default=1, description="Unit multiplier (e.g. 1 for EUR, 100 for JPY)")
    source: str = "NBS"

    model_config = {"from_attributes": True}


class ExchangeRateListResponse(BaseModel):
    """List of exchange rates."""

    data: list[ExchangeRateResponse]
    rate_date: date


class ConversionRequest(BaseModel):
    """Request to convert an amount to RSD."""

    amount: Decimal = Field(gt=0, description="Amount to convert")
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 currency code")
    rate_date: date | None = Field(
        default=None, description="Date for rate lookup (default: today)"
    )


class ConversionResponse(BaseModel):
    """Result of a currency conversion to RSD."""

    rsd_amount: Decimal | None = None
    exchange_rate: Decimal | None = None
    rate_date: date | None = None
    source: str | None = None
    error: str | None = None
