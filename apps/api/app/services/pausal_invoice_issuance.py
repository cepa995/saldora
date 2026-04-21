"""Paušal invoice issuance: sequential numbering + issuance orchestration."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.client import Client
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.invoice_counter import InvoiceCounter
from app.schemas.pausal_invoice import (
    PausalInvoiceIssueRequest,
    PausalInvoiceItem,
)
from app.services import storage
from app.services.pausal_pdf import build_pausal_invoice_pdf

logger = logging.getLogger(__name__)
settings = get_settings()


async def _next_invoice_number(db: AsyncSession, client_id: UUID, year: int) -> str:
    """Atomically compute the next invoice number for a paušalac in a given year.

    Uses ``SELECT ... FOR UPDATE`` row-level locking on the counter row so
    concurrent issuances serialize and numbering is gap-free.

    Args:
        db: Database session.
        client_id: Paušalac Client UUID.
        year: Calendar year (e.g. 2026).

    Returns:
        Invoice number string in the format ``{year}-{NNN}`` (min 3 digits).
    """
    result = await db.execute(
        select(InvoiceCounter)
        .where(InvoiceCounter.client_id == client_id, InvoiceCounter.year == year)
        .with_for_update()
    )
    counter = result.scalar_one_or_none()

    if counter is None:
        counter = InvoiceCounter(client_id=client_id, year=year, last_number=1)
        db.add(counter)
        await db.flush()
    else:
        counter.last_number += 1
        await db.flush()

    number = counter.last_number
    return f"{year}-{number:03d}"


def _customer_snapshot(customer: Customer) -> dict:
    """Return a dict snapshot of a customer suitable for serialisation onto the invoice."""
    return {
        "id": str(customer.id),
        "name": customer.name,
        "is_natural_person": customer.is_natural_person,
        "pib": customer.pib,
        "mb": customer.mb,
        "jmbg": customer.jmbg,
        "address": customer.address,
        "city": customer.city,
        "postal_code": customer.postal_code,
        "country": customer.country,
        "contact_email": customer.contact_email,
        "contact_phone": customer.contact_phone,
    }


def _seller_snapshot(client: Client) -> dict:
    """Return a dict snapshot of a paušalac (seller) at time of issuance."""
    return {
        "id": str(client.id),
        "name": client.name,
        "pib": client.pib,
        "mb": client.mb,
        "address": client.address,
        "city": client.city,
        "postal_code": client.postal_code,
        "bank_account": client.bank_account,
        "activity_code": client.activity_code,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
    }


def _items_payload(items: list[PausalInvoiceItem]) -> tuple[list[dict], Decimal]:
    """Serialise items and compute subtotal.

    Returns:
        A tuple of (serialised_items, subtotal).
    """
    serialised: list[dict] = []
    subtotal = Decimal("0")
    for item in items:
        total = (item.quantity * item.unit_price).quantize(Decimal("0.01"))
        serialised.append(
            {
                "description": item.description,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "unit_price": str(item.unit_price),
                "total": str(total),
            }
        )
        subtotal += total
    return serialised, subtotal


def _require_pausal_fields(client: Client) -> None:
    """Raise 422 if the paušalac Client is missing fields required to issue an invoice."""
    missing: list[str] = []
    if not client.bank_account:
        missing.append("bank_account")
    if not client.activity_code:
        missing.append("activity_code")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "pausal_client_incomplete",
                "missing_fields": missing,
                "message": "Paušalac mora imati popunjen broj računa i šifru delatnosti",
            },
        )


async def _resolve_or_create_customer(
    db: AsyncSession,
    paušalac: Client,
    body: PausalInvoiceIssueRequest,
) -> Customer:
    """Resolve the customer from ``body`` — either by id or by creating a new one."""
    if body.customer_id is not None:
        result = await db.execute(
            select(Customer).where(
                Customer.id == body.customer_id,
                Customer.client_id == paušalac.id,
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    assert body.new_customer is not None
    customer = Customer(
        client_id=paušalac.id,
        organization_id=paušalac.organization_id,
        name=body.new_customer.name,
        is_natural_person=body.new_customer.is_natural_person,
        pib=body.new_customer.pib,
        mb=body.new_customer.mb,
        jmbg=body.new_customer.jmbg,
        address=body.new_customer.address,
        city=body.new_customer.city,
        postal_code=body.new_customer.postal_code,
        country=body.new_customer.country,
        contact_email=body.new_customer.contact_email,
        contact_phone=body.new_customer.contact_phone,
        notes=body.new_customer.notes,
    )
    db.add(customer)
    await db.flush()
    return customer


async def issue_pausal_invoice(
    db: AsyncSession,
    paušalac: Client,
    body: PausalInvoiceIssueRequest,
) -> Invoice:
    """Issue a new outgoing paušal invoice.

    Validates the paušalac has the required fields, resolves/creates the
    customer, reserves the next invoice number atomically, persists an
    Invoice row with ``direction='outgoing'`` and snapshots of seller and
    customer data, then generates and uploads the PDF.

    Args:
        db: Database session (caller is expected to commit).
        paušalac: Paušalac Client issuing the invoice.
        body: Validated issuance request.

    Returns:
        The persisted Invoice (not yet committed; caller commits).
    """
    if paušalac.client_type != "pausalac":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "client_not_pausalac",
                "message": "Samo paušalci mogu izdavati fakture kroz ovaj tok",
            },
        )
    _require_pausal_fields(paušalac)

    customer = await _resolve_or_create_customer(db, paušalac, body)
    invoice_number = await _next_invoice_number(db, paušalac.id, body.invoice_date.year)

    serialised_items, subtotal = _items_payload(body.items)
    invoice_id = uuid4()

    invoice = Invoice(
        id=invoice_id,
        organization_id=paušalac.organization_id,
        client_id=paušalac.id,
        status="issued",
        direction="outgoing",
        invoice_number=invoice_number,
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        seller=_seller_snapshot(paušalac),
        buyer=_customer_snapshot(customer),
        subtotal=subtotal,
        tax_rate=Decimal("0"),
        tax_amount=Decimal("0"),
        total_amount=subtotal,
        currency=body.currency,
        line_items=serialised_items,
    )
    db.add(invoice)
    await db.flush()

    pdf_bytes = build_pausal_invoice_pdf(
        invoice_number=invoice_number,
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        place_of_issue=body.place_of_issue,
        delivery_date=body.delivery_date,
        delivery_place=body.delivery_place,
        seller=_seller_snapshot(paušalac),
        customer=_customer_snapshot(customer),
        items=serialised_items,
        subtotal=subtotal,
        currency=body.currency,
        notes=body.notes,
    )
    key = f"organizations/{paušalac.organization_id}/invoices/{invoice_id}/issued.pdf"
    await asyncio.to_thread(
        storage.get_s3_client().put_object,
        Bucket=settings.storage_bucket,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
        Metadata={"invoice-number": invoice_number},
    )
    invoice.document_path = key
    invoice.document_content_type = "application/pdf"

    logger.info(
        "Issued paušal invoice %s (client=%s, total=%s %s)",
        invoice_number,
        paušalac.id,
        subtotal,
        body.currency,
    )
    return invoice
