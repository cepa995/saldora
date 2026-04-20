"""KPO ledger service — auto-population, manual entries, storno.

The KPO (Knjiga o ostvarenom prometu) is a legally-mandated ledger of
every invoice a paušalac issues. Every issued paušal invoice produces
exactly one KPO entry sharing the same sequential number. Manual entries
may be added for back-filling history, and storno entries reverse prior
entries without mutating them.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_counter import InvoiceCounter
from app.models.kpo_entry import KPOEntry
from app.schemas.kpo import KPOEntryCreate

logger = logging.getLogger(__name__)


async def _next_manual_entry_number(db: AsyncSession, client_id: UUID, year: int) -> str:
    """Reserve the next entry number for a manual KPO entry.

    Uses the shared ``invoice_counters`` row (one per client per year) with
    ``SELECT ... FOR UPDATE`` so manual entries and invoice issuance share
    a single monotonic sequence — the law does not distinguish issuance
    source.

    Args:
        db: Database session.
        client_id: Paušalac Client UUID.
        year: Year of the entry.

    Returns:
        The formatted entry number (e.g. ``2026-017``).
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
    return f"{year}-{counter.last_number:03d}"


async def create_auto_kpo_entry(
    db: AsyncSession,
    paušalac: Client,
    invoice: Invoice,
) -> KPOEntry:
    """Create a KPO entry that mirrors a freshly-issued paušal invoice.

    The KPO entry shares the invoice's ``invoice_number`` as its
    ``entry_number``. The caller (``issue_pausal_invoice``) has already
    reserved that number via the shared counter, so no new counter
    increment is required here.

    Args:
        db: Database session (caller commits).
        paušalac: The Client issuing the invoice.
        invoice: The freshly-created Invoice row.

    Returns:
        The persisted KPOEntry (flushed, not committed).
    """
    buyer = invoice.buyer or {}
    entry = KPOEntry(
        client_id=paušalac.id,
        organization_id=paušalac.organization_id,
        invoice_id=invoice.id,
        year=invoice.invoice_date.year,
        entry_number=invoice.invoice_number or "",
        entry_date=invoice.invoice_date,
        invoice_number=invoice.invoice_number,
        customer_name=buyer.get("name") or "—",
        customer_pib=buyer.get("pib"),
        amount=invoice.total_amount or Decimal("0"),
        currency=invoice.currency or "RSD",
    )
    db.add(entry)
    await db.flush()
    logger.info(
        "Auto-created KPO entry %s for invoice %s (client=%s)",
        entry.entry_number,
        invoice.id,
        paušalac.id,
    )
    return entry


async def create_manual_kpo_entry(
    db: AsyncSession,
    paušalac: Client,
    body: KPOEntryCreate,
) -> KPOEntry:
    """Create a manual KPO entry (for back-filling pre-Saldora history).

    Args:
        db: Database session (caller commits).
        paušalac: The paušalac Client the entry belongs to.
        body: Manual entry payload.

    Returns:
        The persisted KPOEntry (flushed, not committed).
    """
    entry_number = await _next_manual_entry_number(db, paušalac.id, body.entry_date.year)
    entry = KPOEntry(
        client_id=paušalac.id,
        organization_id=paušalac.organization_id,
        invoice_id=None,
        year=body.entry_date.year,
        entry_number=entry_number,
        entry_date=body.entry_date,
        invoice_number=body.invoice_number,
        customer_name=body.customer_name,
        customer_pib=body.customer_pib,
        amount=body.amount,
        currency=body.currency,
        notes=body.notes,
    )
    db.add(entry)
    await db.flush()
    logger.info(
        "Manual KPO entry %s created for client %s (amount=%s)",
        entry_number,
        paušalac.id,
        body.amount,
    )
    return entry


async def storno_kpo_entry(
    db: AsyncSession,
    paušalac: Client,
    original_id: UUID,
    notes: str | None,
) -> KPOEntry:
    """Create a storno (reversal) entry for an existing KPO entry.

    The original entry is marked ``is_cancelled=True`` but kept intact for
    audit integrity. A new entry is inserted with a negated amount and a
    back-reference via ``storno_of_id``. Storno of an already-cancelled
    entry is refused.

    Args:
        db: Database session (caller commits).
        paušalac: The paušalac Client that owns the entry.
        original_id: UUID of the KPO entry to reverse.
        notes: Free-text reason for the storno.

    Returns:
        The newly-created storno KPOEntry.
    """
    result = await db.execute(
        select(KPOEntry).where(
            KPOEntry.id == original_id,
            KPOEntry.client_id == paušalac.id,
        )
    )
    original = result.scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="KPO entry not found")
    if original.is_cancelled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "already_cancelled",
                "message": "Stavka je već stornirana",
            },
        )
    if original.storno_of_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "cannot_storno_storno",
                "message": "Ne može se stornirati storno stavka",
            },
        )

    entry_number = await _next_manual_entry_number(db, paušalac.id, original.entry_date.year)
    reversal = KPOEntry(
        client_id=paušalac.id,
        organization_id=paušalac.organization_id,
        invoice_id=None,
        storno_of_id=original.id,
        year=original.entry_date.year,
        entry_number=entry_number,
        entry_date=original.entry_date,
        invoice_number=original.invoice_number,
        customer_name=original.customer_name,
        customer_pib=original.customer_pib,
        amount=-original.amount,
        currency=original.currency,
        notes=notes,
    )
    db.add(reversal)
    original.is_cancelled = True
    await db.flush()
    logger.info(
        "Storno %s created for KPO entry %s (client=%s, amount=%s)",
        reversal.entry_number,
        original.entry_number,
        paušalac.id,
        reversal.amount,
    )
    return reversal
