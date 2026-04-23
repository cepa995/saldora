"""Client event emission service.

Mirrors the pattern of :mod:`app.services.audit`: a single :func:`emit`
function that adds a ``ClientEvent`` row to the caller's session without
committing, so the event lives in the same transaction as the business
operation that produced it.

The Timeline tab of the client workspace (M19) reads these rows for one
client at a time; the portfolio view (M19.7) aggregates across clients.

Event types are defined as string constants — canonical names are kept
close to the emitters so drift is easy to spot during review.
"""

from __future__ import annotations

import logging
from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client_event import ClientEvent

logger = logging.getLogger(__name__)


# --- Canonical event types ---------------------------------------------------
#
# Keep this set small. Prefer "nouns in the system happened" over verb
# phrases. New types go here as new emit sites land; don't ad-hoc string
# literals in callers.

INVOICE_UPLOADED: Final[str] = "invoice_uploaded"
INVOICE_VERIFIED: Final[str] = "invoice_verified"
INVOICE_EXPORTED: Final[str] = "invoice_exported"
ACCOUNTING_INTENT_CLASSIFIED: Final[str] = "accounting_intent_classified"
RULE_FIRED: Final[str] = "rule_fired"
CLIENT_ASSIGNED: Final[str] = "client_assigned"


async def emit(
    *,
    db: AsyncSession,
    event_type: str,
    organization_id: UUID,
    client_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    payload: dict | None = None,
) -> ClientEvent:
    """Create a ClientEvent row inside the caller's transaction.

    Follows the ``audit.log()`` contract: the row is added to ``db`` but
    NOT committed. The caller owns commit/rollback, so the event is only
    persisted when the business operation that emitted it also commits.

    Args:
        db: Async session in the caller's transaction.
        event_type: One of the module-level event type constants.
        organization_id: Required — every event belongs to an org for scoping.
        client_id: The client the event is about. May be ``None`` for events
            emitted before a client is assigned (e.g. invoice uploaded with
            no client_id yet). Such events are filtered out of per-client
            timelines but remain visible in portfolio-wide audit.
        entity_type: Name of the underlying entity ("invoice", "rule", …).
        entity_id: Primary key of the underlying entity. Enables click-
            through from the timeline row to the entity detail page.
        actor_user_id: User who performed the action. ``None`` for
            system-driven events (e.g. automation rules firing in a worker).
        payload: Small JSON blob with a short human-readable ``summary``
            and any identifiers useful on the timeline row. Keep it small —
            full data stays in the referenced entity.

    Returns:
        The persisted-in-session ``ClientEvent``. Caller typically does
        not need to use the return value.
    """
    event = ClientEvent(
        organization_id=organization_id,
        client_id=client_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        payload=payload or {},
    )
    db.add(event)
    try:
        await db.flush()
    except Exception:
        # Emitters must never break the business operation they instrument.
        # Log and continue; the audit log already records the mutation.
        logger.exception(
            "ClientEvent emit failed (event_type=%s, client_id=%s). "
            "Continuing without event to avoid breaking caller.",
            event_type,
            client_id,
        )
    return event
