"""Client schemas — create, update, response, list."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ClientType = Literal["vat_payer", "pausalac", "foreign_entity", "non_profit"]


class ClientCreate(BaseModel):
    """Schema for creating a client.

    Args:
        name: Client company name.
        pib: Tax ID (PIB) — required for auto-assignment.
        mb: Business registration number (Matični broj).
        address: Street address.
        city: City name.
        postal_code: Postal code.
        contact_email: Primary contact email.
        contact_phone: Primary contact phone.
        notes: Free-text notes about the client.
    """

    name: str = Field(max_length=255)
    pib: str = Field(max_length=20, description="Tax ID (PIB)")
    mb: str | None = Field(default=None, max_length=20)
    client_type: ClientType = Field(default="vat_payer")
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    bank_account: str | None = Field(default=None, max_length=40)
    activity_code: str | None = Field(default=None, max_length=10)


class ClientUpdate(BaseModel):
    """Schema for updating a client (all fields optional).

    Args:
        name: Client company name.
        pib: Tax ID (PIB).
        mb: Business registration number.
        address: Street address.
        city: City name.
        postal_code: Postal code.
        contact_email: Primary contact email.
        contact_phone: Primary contact phone.
        is_active: Active status.
        notes: Free-text notes.
    """

    name: str | None = Field(default=None, max_length=255)
    pib: str | None = Field(default=None, max_length=20)
    mb: str | None = None
    client_type: ClientType | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    bank_account: str | None = Field(default=None, max_length=40)
    activity_code: str | None = Field(default=None, max_length=10)


class ClientSummary(BaseModel):
    """Minimal client info for embedding in invoice responses.

    Args:
        id: Client UUID.
        name: Client company name.
        pib: Tax ID (PIB).
    """

    id: UUID
    name: str
    pib: str
    client_type: ClientType = "vat_payer"

    model_config = {"from_attributes": True}


class ClientResponse(BaseModel):
    """Full client response with invoice statistics.

    Args:
        id: Client UUID.
        organization_id: Owning organization UUID.
        name: Client company name.
        pib: Tax ID (PIB).
        mb: Business registration number.
        address: Street address.
        city: City name.
        postal_code: Postal code.
        contact_email: Primary contact email.
        contact_phone: Primary contact phone.
        is_active: Active status.
        notes: Free-text notes.
        invoice_count: Number of invoices assigned to this client.
        total_amount: Sum of total_amount across client invoices.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID
    organization_id: UUID
    name: str
    pib: str
    mb: str | None = None
    client_type: ClientType = "vat_payer"
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool
    notes: str | None = None
    bank_account: str | None = None
    activity_code: str | None = None
    invoice_count: int = Field(default=0)
    total_amount: str | None = Field(default=None)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    """Paginated list of clients.

    Args:
        data: List of client responses.
        pagination: Pagination metadata.
    """

    data: list[ClientResponse]
    pagination: dict = Field(
        default_factory=lambda: {
            "page": 1,
            "per_page": 20,
            "total": 0,
            "total_pages": 0,
        }
    )
