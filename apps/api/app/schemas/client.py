"""Client schemas — create, update, response, list."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Allowed values for the hospitality-classification fields. Mirrors the
# obligation-matrix consumer in app.services.hospitality_forms. Keep in
# sync with the SRS §4.19.2 table.
LegalForm = Literal["DOO", "preduzetnik", "paušalac", "drugo"]
BookkeepingSystem = Literal["dvojno", "prosto"]


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
        legal_form: Client's legal form (drives obligation matrix; SRS §4.19.2).
        bookkeeping_system: Client's bookkeeping system (drives obligation matrix).
        notes: Free-text notes about the client.
    """

    name: str = Field(max_length=255)
    pib: str = Field(max_length=20, description="Tax ID (PIB)")
    mb: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    legal_form: LegalForm | None = None
    bookkeeping_system: BookkeepingSystem | None = None
    notes: str | None = None


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
        legal_form: Client's legal form (drives obligation matrix; SRS §4.19.2).
        bookkeeping_system: Client's bookkeeping system (drives obligation matrix).
        is_active: Active status.
        notes: Free-text notes.
    """

    name: str | None = Field(default=None, max_length=255)
    pib: str | None = Field(default=None, max_length=20)
    mb: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    legal_form: LegalForm | None = None
    bookkeeping_system: BookkeepingSystem | None = None
    is_active: bool | None = None
    notes: str | None = None


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
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    legal_form: str | None = None
    bookkeeping_system: str | None = None
    is_active: bool
    notes: str | None = None
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


class ClientObligationsResponse(BaseModel):
    """Obligation matrix for one hospitality client.

    Drives the "Obavezni obrasci" card in the per-client Izveštaji tab.
    Backed by `app.services.hospitality_forms.required_forms`. See
    SRS §4.19 for the legal basis.

    Args:
        legal_form: The client's classification at the time of the call
            (echoed so the frontend can label the card).
        bookkeeping_system: Same.
        forms: Form key → status. Status values are documented in
            `hospitality_forms.FormStatus`.
    """

    legal_form: str | None
    bookkeeping_system: str | None
    forms: dict[str, str]
