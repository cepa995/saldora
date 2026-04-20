"""Pydantic schemas for Customer (buyer of paušal invoices)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """Schema for creating a customer under a paušalac client."""

    name: str = Field(max_length=255)
    is_natural_person: bool = False
    pib: str | None = Field(default=None, max_length=20)
    mb: str | None = Field(default=None, max_length=20)
    jmbg: str | None = Field(default=None, max_length=13)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(default="RS", max_length=2)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class CustomerUpdate(BaseModel):
    """Schema for partial update of a customer."""

    name: str | None = Field(default=None, max_length=255)
    is_natural_person: bool | None = None
    pib: str | None = Field(default=None, max_length=20)
    mb: str | None = Field(default=None, max_length=20)
    jmbg: str | None = Field(default=None, max_length=13)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=2)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    is_active: bool | None = None


class CustomerResponse(BaseModel):
    """Customer response body."""

    id: UUID
    client_id: UUID
    name: str
    is_natural_person: bool
    pib: str | None = None
    mb: str | None = None
    jmbg: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str = "RS"
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    """Paginated list of customers."""

    data: list[CustomerResponse]
    pagination: dict
