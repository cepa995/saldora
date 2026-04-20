"""Schemas for KPO ledger entries."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class KPOEntryCreate(BaseModel):
    """Manual KPO entry (back-fill of pre-Saldora history).

    For automated entries created from issued invoices, the service
    does not use this schema — it constructs the entry directly.
    """

    entry_date: date
    invoice_number: str | None = Field(default=None, max_length=100)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_pib: str | None = Field(default=None, max_length=20)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="RSD", min_length=3, max_length=3)
    notes: str | None = None


class KPOEntryStornoRequest(BaseModel):
    """Request to storno (reverse) an existing KPO entry."""

    notes: str | None = Field(
        default=None,
        description="Razlog storniranja (reason for the storno)",
    )


class KPOEntryResponse(BaseModel):
    """A single KPO entry in API responses."""

    id: UUID
    client_id: UUID
    invoice_id: UUID | None = None
    storno_of_id: UUID | None = None
    year: int
    entry_number: str
    entry_date: date
    invoice_number: str | None = None
    customer_name: str
    customer_pib: str | None = None
    amount: Decimal
    currency: str
    notes: str | None = None
    is_cancelled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KPOListResponse(BaseModel):
    """Paginated KPO ledger list."""

    data: list[KPOEntryResponse]
    pagination: dict
