"""Pydantic schemas for paušal invoice issuance (outgoing)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.customer import CustomerCreate


class PausalInvoiceItem(BaseModel):
    """A single line item on a paušal invoice."""

    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="kom", max_length=20)
    unit_price: Decimal = Field(ge=0)


class PausalInvoiceIssueRequest(BaseModel):
    """Request to issue a new outgoing paušal invoice.

    Exactly one of ``customer_id`` or ``new_customer`` must be provided.
    """

    customer_id: UUID | None = None
    new_customer: CustomerCreate | None = None

    invoice_date: date
    due_date: date | None = None
    place_of_issue: str = Field(min_length=1, max_length=100)
    delivery_date: date | None = None
    delivery_place: str | None = Field(default=None, max_length=100)

    items: list[PausalInvoiceItem] = Field(min_length=1)
    currency: str = Field(default="RSD", min_length=3, max_length=3)
    notes: str | None = None

    @model_validator(mode="after")
    def _exactly_one_customer(self) -> PausalInvoiceIssueRequest:
        if (self.customer_id is None) == (self.new_customer is None):
            raise ValueError("Provide exactly one of customer_id or new_customer")
        return self


class PausalInvoiceResponse(BaseModel):
    """Response body after issuing a paušal invoice."""

    id: UUID
    invoice_number: str
    status: str
    direction: str
    client_id: UUID
    customer_snapshot: dict
    seller_snapshot: dict
    invoice_date: date
    due_date: date | None = None
    place_of_issue: str | None = None
    delivery_date: date | None = None
    delivery_place: str | None = None
    items: list[PausalInvoiceItem]
    currency: str
    subtotal: Decimal
    total_amount: Decimal
    notes: str | None = None
    pdf_url: str | None = None
    created_at: datetime
