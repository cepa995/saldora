"""Clients CRUD router — Agency plan only."""

import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_feature, require_role
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.user import User
from app.plans import Feature
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_feature(Feature.CLIENT_MANAGEMENT))])


def _build_client_response(client: Client, invoice_count: int, total_amount: float | None) -> dict:
    """Build a ClientResponse dict from a Client model and computed stats.

    Args:
        client: Client model instance.
        invoice_count: Number of invoices for this client.
        total_amount: Sum of total_amount for client invoices.

    Returns:
        Dict suitable for ClientResponse serialization.
    """
    return {
        "id": client.id,
        "organization_id": client.organization_id,
        "name": client.name,
        "pib": client.pib,
        "mb": client.mb,
        "address": client.address,
        "city": client.city,
        "postal_code": client.postal_code,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
        "is_active": client.is_active,
        "notes": client.notes,
        "invoice_count": invoice_count,
        "total_amount": str(total_amount) if total_amount is not None else None,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> dict:
    """Create a client for the current organization.

    Args:
        body: Client creation schema.

    Returns:
        Created client with stats.

    Raises:
        HTTPException: 409 if PIB already exists for this organization.
    """
    client = Client(
        organization_id=user.organization_id,
        name=body.name,
        pib=body.pib,
        mb=body.mb,
        address=body.address,
        city=body.city,
        postal_code=body.postal_code,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        notes=body.notes,
    )
    db.add(client)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Klijent sa PIB-om {body.pib} već postoji",
        )
    await db.refresh(client)

    # Retroactively assign unassigned invoices matching this client's PIB
    assigned_count = await _retroactive_client_assignment(db, client)
    logger.info(
        "Client %s created (PIB: %s), retroactively assigned %d invoices",
        client.id,
        client.pib,
        assigned_count,
    )

    return _build_client_response(client, invoice_count=assigned_count, total_amount=None)


@router.get("/", response_model=ClientListResponse)
async def list_clients(
    search: str | None = Query(default=None, description="Search by name or PIB"),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> dict:
    """List clients for the current organization.

    Args:
        search: Optional search term (ILIKE on name/PIB).
        is_active: Optional filter by active status.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Paginated list of clients with invoice stats.
    """
    conditions = [Client.organization_id == user.organization_id]
    if search:
        term = f"%{search}%"
        conditions.append(or_(Client.name.ilike(term), Client.pib.ilike(term)))
    if is_active is not None:
        conditions.append(Client.is_active == is_active)

    # Count
    count_result = await db.execute(select(func.count(Client.id)).where(and_(*conditions)))
    total = count_result.scalar() or 0
    total_pages = math.ceil(total / per_page) if total > 0 else 0

    # Fetch clients
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Client)
        .where(and_(*conditions))
        .order_by(Client.name.asc())
        .offset(offset)
        .limit(per_page)
    )
    clients = list(result.scalars().all())

    # Batch-load invoice stats
    client_ids = [c.id for c in clients]
    stats_map: dict[UUID, tuple[int, float | None]] = {cid: (0, None) for cid in client_ids}

    if client_ids:
        stats_result = await db.execute(
            select(
                Invoice.client_id,
                func.count(Invoice.id).label("cnt"),
                func.sum(Invoice.total_amount).label("total"),
            )
            .where(Invoice.client_id.in_(client_ids))
            .group_by(Invoice.client_id)
        )
        for row in stats_result.all():
            stats_map[row[0]] = (row[1], float(row[2]) if row[2] is not None else None)

    data = [_build_client_response(c, *stats_map[c.id]) for c in clients]

    return {
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> dict:
    """Get a single client by ID.

    Args:
        client_id: Client UUID.

    Returns:
        Client with invoice stats.

    Raises:
        HTTPException: 404 if client not found or not in user's org.
    """
    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Klijent nije pronađen")

    stats_result = await db.execute(
        select(
            func.count(Invoice.id).label("cnt"),
            func.sum(Invoice.total_amount).label("total"),
        ).where(Invoice.client_id == client_id)
    )
    row = stats_result.one()
    return _build_client_response(
        client,
        invoice_count=row[0],
        total_amount=float(row[1]) if row[1] is not None else None,
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> dict:
    """Update a client.

    Args:
        client_id: Client UUID.
        body: Partial update schema.

    Returns:
        Updated client with invoice stats.

    Raises:
        HTTPException: 404 if not found, 409 if PIB conflict.
    """
    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Klijent nije pronađen")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Klijent sa PIB-om {body.pib} već postoji",
        )
    await db.refresh(client)

    stats_result = await db.execute(
        select(
            func.count(Invoice.id).label("cnt"),
            func.sum(Invoice.total_amount).label("total"),
        ).where(Invoice.client_id == client_id)
    )
    row = stats_result.one()
    return _build_client_response(
        client,
        invoice_count=row[0],
        total_amount=float(row[1]) if row[1] is not None else None,
    )


@router.post("/{client_id}/toggle-active", status_code=status.HTTP_200_OK)
async def toggle_client_active(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> dict:
    """Toggle client active/inactive status.

    Args:
        client_id: Client UUID.

    Returns:
        Updated client with new is_active status.
    """
    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Klijent nije pronađen")

    client.is_active = not client.is_active
    await db.commit()
    await db.refresh(client)
    return {"id": str(client.id), "name": client.name, "is_active": client.is_active}


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> None:
    """Permanently delete a client.

    Unlinks all invoices and line items from this client before deletion.
    Requires admin role.

    Args:
        client_id: Client UUID.

    Raises:
        HTTPException: 404 if not found or not in user's org.
    """
    from sqlalchemy import update

    from app.models.line_item import InvoiceLineItem

    result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Klijent nije pronađen")

    # Unlink invoices and line items
    await db.execute(update(Invoice).where(Invoice.client_id == client_id).values(client_id=None))
    await db.execute(
        update(InvoiceLineItem).where(InvoiceLineItem.client_id == client_id).values(client_id=None)
    )

    await db.delete(client)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _retroactive_client_assignment(
    db: AsyncSession,
    client: Client,
) -> int:
    """Assign unassigned invoices to the newly created client by PIB match.

    Scans all invoices in the same organization where:
    - client_id is NULL
    - seller.pib matches the client's PIB

    Also updates corresponding invoice_line_items rows.

    Args:
        db: Active database session.
        client: The newly created Client.

    Returns:
        Number of invoices assigned.
    """
    from sqlalchemy import update

    from app.models.line_item import InvoiceLineItem

    # Find unassigned invoices where seller PIB matches
    result = await db.execute(
        select(Invoice).where(
            Invoice.organization_id == client.organization_id,
            Invoice.client_id.is_(None),
        )
    )
    invoices = result.scalars().all()

    assigned = 0
    for inv in invoices:
        seller = inv.seller if isinstance(inv.seller, dict) else {}
        if seller.get("pib") == client.pib:
            inv.client_id = client.id
            assigned += 1

    if assigned:
        # Also update denormalized line items
        await db.execute(
            update(InvoiceLineItem)
            .where(
                InvoiceLineItem.organization_id == client.organization_id,
                InvoiceLineItem.seller_pib == client.pib,
                InvoiceLineItem.client_id.is_(None),
            )
            .values(client_id=client.id)
        )
        await db.commit()

    return assigned
