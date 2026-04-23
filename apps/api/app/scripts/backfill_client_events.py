"""Backfill client_events from existing historical data.

Run once after migration 0014 to populate the per-client timeline
from tables that already record the relevant activity:

* ``invoices`` (uploaded, verified, exported status transitions)
* ``audit_logs`` (actor and timestamp for create / verify / assign)

The script is idempotent: it uses a deterministic, content-derived UUID
per (event_type, invoice_id) pair so re-running skips rows already
inserted.

Usage::

    cd apps/api && python -m app.scripts.backfill_client_events

Options::

    --dry-run   print counts only, do not write
    --org-id    limit to a single organization
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.audit_log import AuditLog
from app.models.client_event import ClientEvent
from app.models.invoice import Invoice
from app.services.events import (
    CLIENT_ASSIGNED,
    INVOICE_EXPORTED,
    INVOICE_UPLOADED,
    INVOICE_VERIFIED,
)

# Stable namespace used to derive deterministic IDs for backfilled events.
# The same source row will always hash to the same event id, making the
# backfill safe to re-run.
_BACKFILL_NAMESPACE = uuid.UUID("0f2a6e8a-a2c1-4f0b-8a1c-c1b5e9f6d3a1")


def _derive_event_id(event_type: str, source_id: uuid.UUID) -> uuid.UUID:
    """Return a deterministic UUID for a (type, source) pair."""
    return uuid.uuid5(_BACKFILL_NAMESPACE, f"{event_type}:{source_id}")


def _audit_by_action_entity(
    audit_rows: list[AuditLog],
) -> dict[tuple[str, uuid.UUID], AuditLog]:
    """Index audit rows by (action, entity_id) for O(1) lookup."""
    idx: dict[tuple[str, uuid.UUID], AuditLog] = {}
    for row in audit_rows:
        if row.entity_id is None:
            continue
        idx[(row.action, row.entity_id)] = row
    return idx


async def _emit_historical(
    db: AsyncSession,
    event_type: str,
    invoice: Invoice,
    when: datetime,
    payload: dict[str, Any],
    actor_id: uuid.UUID | None,
    dry_run: bool,
) -> None:
    """Insert one backfilled event, idempotent on re-run."""
    if dry_run:
        return
    await db.execute(
        pg_insert(ClientEvent.__table__)
        .values(
            id=_derive_event_id(event_type, invoice.id),
            organization_id=invoice.organization_id,
            client_id=invoice.client_id,
            event_type=event_type,
            event_date=when,
            payload=payload,
            entity_type="invoice",
            entity_id=invoice.id,
            actor_user_id=actor_id,
            created_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )


async def _process_invoice(
    db: AsyncSession,
    invoice: Invoice,
    audit_index: dict[tuple[str, uuid.UUID], AuditLog],
    dry_run: bool,
    counts: dict[str, int],
) -> None:
    """Emit every relevant historical event for one invoice."""
    upload_audit = audit_index.get(("invoice.create", invoice.id))
    verify_audit = audit_index.get(("invoice.verify", invoice.id))
    assign_audit = audit_index.get(("invoice.assign_client", invoice.id))

    # Every invoice has an upload event.
    await _emit_historical(
        db,
        INVOICE_UPLOADED,
        invoice,
        invoice.created_at,
        {
            "content_type": invoice.document_content_type,
            "document_hash": invoice.document_hash,
        },
        upload_audit.user_id if upload_audit else None,
        dry_run,
    )
    counts[INVOICE_UPLOADED] += 1

    # Verified event — only if the invoice progressed past review.
    if invoice.status in ("verified", "exported"):
        when = verify_audit.created_at if verify_audit else invoice.updated_at
        await _emit_historical(
            db,
            INVOICE_VERIFIED,
            invoice,
            when,
            {
                "invoice_number": invoice.invoice_number,
                "total_amount": (
                    str(invoice.total_amount) if invoice.total_amount is not None else None
                ),
                "currency": invoice.currency,
            },
            verify_audit.user_id if verify_audit else None,
            dry_run,
        )
        counts[INVOICE_VERIFIED] += 1

    # Exported event — only for status=exported.
    if invoice.status == "exported":
        await _emit_historical(
            db,
            INVOICE_EXPORTED,
            invoice,
            invoice.updated_at,
            {
                "invoice_number": invoice.invoice_number,
                "destination": "backfilled",
            },
            verify_audit.user_id if verify_audit else None,
            dry_run,
        )
        counts[INVOICE_EXPORTED] += 1

    # Client-assigned — only for invoices that currently have a client.
    # Auto-assignment historically did not audit, so we fall back to the
    # invoice's updated_at when no assign audit exists.
    if invoice.client_id is not None:
        when = assign_audit.created_at if assign_audit else invoice.updated_at
        await _emit_historical(
            db,
            CLIENT_ASSIGNED,
            invoice,
            when,
            {
                "invoice_number": invoice.invoice_number,
                "backfilled": True,
            },
            assign_audit.user_id if assign_audit else None,
            dry_run,
        )
        counts[CLIENT_ASSIGNED] += 1


async def backfill(dry_run: bool = False, org_id: str | None = None) -> None:
    """Scan invoices + audit_logs and emit historical client events."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Load relevant audit logs for actor / timestamp recovery.
        audit_conditions = [
            AuditLog.entity_type == "invoice",
            AuditLog.action.in_(["invoice.create", "invoice.verify", "invoice.assign_client"]),
        ]
        if org_id:
            audit_conditions.append(AuditLog.organization_id == uuid.UUID(org_id))
        audit_result = await db.execute(select(AuditLog).where(and_(*audit_conditions)))
        audit_index = _audit_by_action_entity(list(audit_result.scalars().all()))

        # Invoices to process.
        invoice_stmt = select(Invoice)
        if org_id:
            invoice_stmt = invoice_stmt.where(Invoice.organization_id == uuid.UUID(org_id))
        invoices = list((await db.execute(invoice_stmt)).scalars().all())
        print(f"Found {len(invoices)} invoices to scan")

        counts: dict[str, int] = defaultdict(int)
        for idx, invoice in enumerate(invoices, start=1):
            await _process_invoice(db, invoice, audit_index, dry_run, counts)
            if not dry_run and idx % 100 == 0:
                await db.commit()
                print(f"  committed {idx}/{len(invoices)}")

        if not dry_run:
            await db.commit()

        print("Backfill summary:")
        for k in sorted(counts):
            print(f"  {k}: {counts[k]}")
        if dry_run:
            print("(dry run — no changes written)")

    await engine.dispose()


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not write events.")
    parser.add_argument("--org-id", default=None, help="Restrict to one org UUID.")
    args = parser.parse_args()
    try:
        asyncio.run(backfill(dry_run=args.dry_run, org_id=args.org_id))
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    _main()
