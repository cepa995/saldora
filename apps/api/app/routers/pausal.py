"""Paušal module — customers CRUD and outgoing invoice issuance."""

from __future__ import annotations

import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_feature, require_role
from app.models.client import Client
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.kpo_entry import KPOEntry
from app.models.user import User
from app.plans import Feature
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.kpo import (
    KPOEntryCreate,
    KPOEntryResponse,
    KPOEntryStornoRequest,
    KPOListResponse,
)
from app.schemas.pausal_invoice import (
    PausalInvoiceIssueRequest,
    PausalInvoiceResponse,
)
from app.schemas.revenue import RevenueStatusResponse
from app.services import storage
from app.services.kpo_ledger import create_manual_kpo_entry, storno_kpo_entry
from app.services.pausal_invoice_issuance import issue_pausal_invoice
from app.services.revenue_tracking import compute_revenue_status

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_feature(Feature.CLIENT_MANAGEMENT))])


async def _get_pausalac(db: AsyncSession, client_id: UUID, organization_id: UUID) -> Client:
    """Load a Client, require it to belong to the org and be a paušalac."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.organization_id == organization_id,
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if client.client_type != "pausalac":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "client_not_pausalac",
                "message": "Klijent nije paušalac",
            },
        )
    return client


def _invoice_to_pausal_response(invoice: Invoice, pdf_url: str | None) -> dict:
    """Build a PausalInvoiceResponse dict from a persisted Invoice row."""
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "direction": invoice.direction,
        "client_id": invoice.client_id,
        "customer_snapshot": invoice.buyer or {},
        "seller_snapshot": invoice.seller or {},
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "place_of_issue": (invoice.buyer or {}).get("_place_of_issue"),
        "delivery_date": None,
        "delivery_place": None,
        "items": invoice.line_items or [],
        "currency": invoice.currency,
        "subtotal": invoice.subtotal,
        "total_amount": invoice.total_amount,
        "notes": None,
        "pdf_url": pdf_url,
        "created_at": invoice.created_at,
    }


# ---------------------------------------------------------------------------
# Customers CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/{client_id}/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    client_id: UUID,
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> Customer:
    """Create a customer under a paušalac Client."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    customer = Customer(
        client_id=paušalac.id,
        organization_id=paušalac.organization_id,
        name=body.name,
        is_natural_person=body.is_natural_person,
        pib=body.pib,
        mb=body.mb,
        jmbg=body.jmbg,
        address=body.address,
        city=body.city,
        postal_code=body.postal_code,
        country=body.country,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        notes=body.notes,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("/{client_id}/customers", response_model=CustomerListResponse)
async def list_customers(
    client_id: UUID,
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> dict:
    """List customers for a paušalac Client."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)

    conditions = [Customer.client_id == paušalac.id]
    if is_active is not None:
        conditions.append(Customer.is_active == is_active)
    if search:
        term = f"%{search}%"
        conditions.append(
            or_(
                Customer.name.ilike(term),
                Customer.pib.ilike(term),
                Customer.jmbg.ilike(term),
            )
        )

    total_result = await db.execute(select(func.count(Customer.id)).where(and_(*conditions)))
    total = int(total_result.scalar() or 0)

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Customer)
        .where(and_(*conditions))
        .order_by(Customer.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    customers = result.scalars().all()
    return {
        "data": [CustomerResponse.model_validate(c) for c in customers],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page) if total else 0,
        },
    }


@router.get("/{client_id}/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    client_id: UUID,
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> Customer:
    """Get a single customer by id."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.client_id == paušalac.id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/{client_id}/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    client_id: UUID,
    customer_id: UUID,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> Customer:
    """Partial update of a customer."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.client_id == paušalac.id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete(
    "/{client_id}/customers/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer(
    client_id: UUID,
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> None:
    """Soft-delete a customer (mark is_active=false)."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.client_id == paušalac.id,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Invoice issuance
# ---------------------------------------------------------------------------


@router.post(
    "/{client_id}/invoices",
    response_model=PausalInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_invoice(
    client_id: UUID,
    body: PausalInvoiceIssueRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> dict:
    """Issue a new outgoing paušal invoice."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    invoice = await issue_pausal_invoice(db, paušalac, body)
    await db.commit()
    await db.refresh(invoice)

    pdf_url = storage.get_presigned_url(invoice.document_path) if invoice.document_path else None
    return _invoice_to_pausal_response(invoice, pdf_url)


@router.get("/{client_id}/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    client_id: UUID,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("viewer")),
) -> dict:
    """Return a presigned URL to download the paušal invoice PDF."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == paušalac.id,
            Invoice.direction == "outgoing",
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None or not invoice.document_path:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    return {"url": storage.get_presigned_url(invoice.document_path)}


# ---------------------------------------------------------------------------
# KPO ledger
# ---------------------------------------------------------------------------


@router.get("/{client_id}/kpo", response_model=KPOListResponse)
async def list_kpo_entries(
    client_id: UUID,
    year: int | None = Query(default=None),
    include_cancelled: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("viewer")),
) -> dict:
    """List KPO ledger entries for a paušalac, ordered chronologically."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)

    conditions = [KPOEntry.client_id == paušalac.id]
    if year is not None:
        conditions.append(KPOEntry.year == year)
    if not include_cancelled:
        conditions.append(KPOEntry.is_cancelled.is_(False))

    total_result = await db.execute(select(func.count(KPOEntry.id)).where(and_(*conditions)))
    total = int(total_result.scalar() or 0)

    offset = (page - 1) * per_page
    result = await db.execute(
        select(KPOEntry)
        .where(and_(*conditions))
        .order_by(KPOEntry.entry_date.asc(), KPOEntry.entry_number.asc())
        .offset(offset)
        .limit(per_page)
    )
    entries = result.scalars().all()
    return {
        "data": [KPOEntryResponse.model_validate(e) for e in entries],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page) if total else 0,
        },
    }


@router.get("/{client_id}/kpo/{entry_id}", response_model=KPOEntryResponse)
async def get_kpo_entry(
    client_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("viewer")),
) -> KPOEntry:
    """Get a single KPO entry by id."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    result = await db.execute(
        select(KPOEntry).where(
            KPOEntry.id == entry_id,
            KPOEntry.client_id == paušalac.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="KPO entry not found")
    return entry


@router.post(
    "/{client_id}/kpo",
    response_model=KPOEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_kpo_entry_manual(
    client_id: UUID,
    body: KPOEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> KPOEntry:
    """Create a manual KPO entry (for back-filling pre-Saldora history)."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    entry = await create_manual_kpo_entry(db, paušalac, body)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.post(
    "/{client_id}/kpo/{entry_id}/storno",
    response_model=KPOEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def storno_kpo(
    client_id: UUID,
    entry_id: UUID,
    body: KPOEntryStornoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> KPOEntry:
    """Reverse a KPO entry by creating a storno (corrective) entry."""
    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    reversal = await storno_kpo_entry(db, paušalac, entry_id, body.notes)
    await db.commit()
    await db.refresh(reversal)
    return reversal


# ---------------------------------------------------------------------------
# Revenue tracking
# ---------------------------------------------------------------------------


@router.get("/{client_id}/revenue-status", response_model=RevenueStatusResponse)
async def get_revenue_status(
    client_id: UUID,
    year: int | None = Query(
        default=None,
        ge=2000,
        le=2100,
        description="Calendar year to compute (defaults to the current year).",
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("viewer")),
) -> RevenueStatusResponse:
    """Return current revenue and threshold status for a paušalac."""
    from datetime import UTC, datetime

    paušalac = await _get_pausalac(db, client_id, user.organization_id)
    effective_year = year if year is not None else datetime.now(UTC).year
    return await compute_revenue_status(db, paušalac, effective_year)
