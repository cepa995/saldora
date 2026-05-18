"""Clients CRUD router — Agency plan only."""

import logging
import math
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_feature, require_role
from app.models.automation_rule import AutomationRule
from app.models.client import Client
from app.models.client_event import ClientEvent
from app.models.invoice import Invoice
from app.models.rule_client_association import RuleClientAssociation
from app.models.user import User
from app.plans import Feature
from app.schemas.automation_rule import AutomationRuleResponse
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientObligationsResponse,
    ClientResponse,
    ClientUpdate,
)
from app.schemas.client_event import ClientEventListResponse, ClientEventResponse
from app.services.hospitality_forms import required_forms

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
        "legal_form": client.legal_form,
        "bookkeeping_system": client.bookkeeping_system,
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
        legal_form=body.legal_form,
        bookkeeping_system=body.bookkeeping_system,
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


@router.get("/{client_id}/obligations", response_model=ClientObligationsResponse)
async def get_client_obligations(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> ClientObligationsResponse:
    """Return the hospitality obligation matrix for one client.

    Drives the "Obavezni obrasci" card on the per-client Izveštaji tab.
    Resolved entirely from `(legal_form, bookkeeping_system)` via
    `required_forms`; the frontend never re-derives.

    Args:
        client_id: Client UUID.

    Returns:
        The obligation matrix plus the classification the matrix was
        computed from.

    Raises:
        HTTPException: 404 if client not found or not in user's org.
    """
    result = await db.execute(
        select(Client.legal_form, Client.bookkeeping_system).where(
            and_(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Klijent nije pronađen")
    legal_form, bookkeeping_system = row

    matrix = required_forms(legal_form=legal_form, bookkeeping_system=bookkeeping_system)
    return ClientObligationsResponse(
        legal_form=legal_form,
        bookkeeping_system=bookkeeping_system,
        forms=dict(matrix),  # FormKey/FormStatus Literals serialize as plain strings
    )


@router.get("/{client_id}/events", response_model=ClientEventListResponse)
async def list_client_events(
    client_id: UUID,
    period: str | None = Query(
        default=None,
        description="YYYY-MM — filter events that happened within the calendar month.",
    ),
    event_type: str | None = Query(
        default=None,
        description="Filter by event_type (see app.services.events constants).",
    ),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> dict:
    """Return the client's chronological event stream.

    The Timeline tab of the client workspace (M19) calls this endpoint.
    Ordered newest-first.
    """
    # Verify the client belongs to the user's org
    client_result = await db.execute(
        select(Client).where(
            and_(
                Client.id == client_id,
                Client.organization_id == user.organization_id,
            )
        )
    )
    if client_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Klijent nije pronađen",
        )

    conditions = [
        ClientEvent.client_id == client_id,
        ClientEvent.organization_id == user.organization_id,
    ]
    if event_type:
        conditions.append(ClientEvent.event_type == event_type)
    if period:
        # Parse "YYYY-MM". Reject anything else with a 400.
        try:
            year_str, month_str = period.split("-", 1)
            year = int(year_str)
            month_num = int(month_str)
            if not 1 <= month_num <= 12:
                raise ValueError
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period format; expected YYYY-MM",
            ) from None
        from datetime import datetime as _dt

        start = _dt(year, month_num, 1, tzinfo=UTC)
        end_year, end_month = (year + 1, 1) if month_num == 12 else (year, month_num + 1)
        end = _dt(end_year, end_month, 1, tzinfo=UTC)
        conditions.append(ClientEvent.event_date >= start)
        conditions.append(ClientEvent.event_date < end)

    count_result = await db.execute(select(func.count(ClientEvent.id)).where(and_(*conditions)))
    total = count_result.scalar() or 0
    total_pages = math.ceil(total / per_page) if total else 0

    offset = (page - 1) * per_page
    result = await db.execute(
        select(ClientEvent)
        .where(and_(*conditions))
        .order_by(ClientEvent.event_date.desc(), ClientEvent.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    events_rows = list(result.scalars().all())

    return {
        "data": [ClientEventResponse.model_validate(e) for e in events_rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }


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

    Scans all invoices in the same organization where ``client_id`` is
    NULL and either side of the invoice matches the client's PIB. **Buyer
    side wins** — in the hospitality agency workflow the agency's client
    is the BUYER of supplier invoices; the seller-side check is a
    fallback that covers outgoing-invoice flows (the agency's client
    issued the invoice themselves).

    Mirrors the at-upload assignment in
    ``workers/ocr_worker/tasks.py::_auto_assign_client`` so both code
    paths reach the same answer.

    Also updates ``invoice_line_items.client_id`` for every line of
    every newly assigned invoice. The bulk update is keyed by
    ``invoice_id`` rather than by PIB because the denormalized table
    only carries ``seller_pib`` — a buyer-side match would silently miss
    all the rows otherwise.

    Args:
        db: Active database session.
        client: The newly created Client.

    Returns:
        Number of invoices assigned.
    """
    from sqlalchemy import update

    from app.models.line_item import InvoiceLineItem
    from app.services import events

    result = await db.execute(
        select(Invoice).where(
            Invoice.organization_id == client.organization_id,
            Invoice.client_id.is_(None),
        )
    )
    invoices = result.scalars().all()

    assigned_ids: list = []
    for inv in invoices:
        buyer = inv.buyer if isinstance(inv.buyer, dict) else {}
        seller = inv.seller if isinstance(inv.seller, dict) else {}
        if buyer.get("pib") == client.pib:
            match_side = "buyer"
        elif seller.get("pib") == client.pib:
            match_side = "seller"
        else:
            continue

        inv.client_id = client.id
        assigned_ids.append(inv.id)
        # One timeline event per auto-assigned invoice. The actor is
        # None: auto-assignment happens as a side effect of creating a
        # client, not as a direct user action on the invoice.
        await events.emit(
            db=db,
            event_type=events.CLIENT_ASSIGNED,
            organization_id=client.organization_id,
            client_id=client.id,
            entity_type="invoice",
            entity_id=inv.id,
            actor_user_id=None,
            payload={
                "invoice_number": inv.invoice_number,
                "auto_assigned": True,
                "match_reason": f"pib_{match_side}",
            },
        )

    if assigned_ids:
        # Sync the denormalized line_items by invoice_id, not by PIB —
        # buyer-side matches would be missed if we filtered on seller_pib.
        await db.execute(
            update(InvoiceLineItem)
            .where(
                InvoiceLineItem.invoice_id.in_(assigned_ids),
                InvoiceLineItem.client_id.is_(None),
            )
            .values(client_id=client.id)
        )
        await db.commit()

    return len(assigned_ids)


# ---------------------------------------------------------------------------
# Per-client rule attachments
# ---------------------------------------------------------------------------


async def _ensure_client_in_org(db: AsyncSession, client_id: UUID, organization_id: UUID) -> Client:
    """Load a client and verify it belongs to the given org, or raise 404."""
    result = await db.execute(
        select(Client).where(
            and_(Client.id == client_id, Client.organization_id == organization_id)
        )
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Klijent nije pronađen")
    return client


async def _ensure_rule_in_org(
    db: AsyncSession, rule_id: UUID, organization_id: UUID
) -> AutomationRule:
    """Load a rule (with associations) and verify it belongs to the given org."""
    result = await db.execute(
        select(AutomationRule)
        .where(
            and_(
                AutomationRule.id == rule_id,
                AutomationRule.organization_id == organization_id,
            )
        )
        .options(selectinload(AutomationRule.client_associations))
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Pravilo nije pronađeno")
    return rule


@router.get("/{client_id}/rules", response_model=list[AutomationRuleResponse])
async def list_client_rules(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator")),
) -> list[AutomationRule]:
    """Return the rules explicitly scoped to this client.

    Global rules (rules with zero client associations) are NOT returned here;
    they apply to every invoice in the org and belong to the agency-wide
    /api/v1/rules surface.
    """
    await _ensure_client_in_org(db, client_id, user.organization_id)

    result = await db.execute(
        select(AutomationRule)
        .join(
            RuleClientAssociation,
            RuleClientAssociation.rule_id == AutomationRule.id,
        )
        .where(
            and_(
                AutomationRule.organization_id == user.organization_id,
                RuleClientAssociation.client_id == client_id,
            )
        )
        .options(selectinload(AutomationRule.client_associations))
        .order_by(AutomationRule.priority.asc(), AutomationRule.created_at.asc())
    )
    return list(result.scalars().all())


@router.post(
    "/{client_id}/rules/{rule_id}",
    response_model=AutomationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_rule_to_client(
    client_id: UUID,
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> AutomationRule:
    """Attach a rule to this client.

    Idempotent — attaching a rule that's already attached is a no-op and
    still returns the current rule state.
    """
    await _ensure_client_in_org(db, client_id, user.organization_id)
    rule = await _ensure_rule_in_org(db, rule_id, user.organization_id)

    already_attached = any(assoc.client_id == client_id for assoc in rule.client_associations)
    if not already_attached:
        rule.client_associations.append(RuleClientAssociation(rule_id=rule_id, client_id=client_id))
        try:
            await db.commit()
        except IntegrityError:
            # Race: another request attached at the same time. Recover gracefully.
            await db.rollback()
        # Re-load with fresh associations so the response includes the new attach.
        db.expire(rule, ["client_associations"])
        result = await db.execute(
            select(AutomationRule)
            .where(AutomationRule.id == rule_id)
            .options(selectinload(AutomationRule.client_associations))
        )
        rule = result.scalar_one()
    return rule


@router.delete(
    "/{client_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_rule_from_client(
    client_id: UUID,
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("manager")),
) -> None:
    """Detach a rule from this client.

    Idempotent — if the rule wasn't attached, the response is still 204.
    """
    await _ensure_client_in_org(db, client_id, user.organization_id)
    await _ensure_rule_in_org(db, rule_id, user.organization_id)

    result = await db.execute(
        select(RuleClientAssociation).where(
            and_(
                RuleClientAssociation.rule_id == rule_id,
                RuleClientAssociation.client_id == client_id,
            )
        )
    )
    assoc = result.scalar_one_or_none()
    if assoc is not None:
        await db.delete(assoc)
        await db.commit()
