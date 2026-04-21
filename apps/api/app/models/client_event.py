"""Client event model.

Append-only per-client event stream. Every action in the app that
touches a specific client writes one row here. The Timeline tab of
the client workspace renders rows from this table for the currently
selected client and period.

Events live in the same transaction as the business operation that
produced them — emitted via :func:`app.services.events.emit` which
adds the row to the caller's session without committing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.organization import Organization
    from app.models.user import User


class ClientEvent(Base, UUIDMixin):
    """One event in a client's chronological feed."""

    __tablename__ = "client_events"

    # Scope
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    # Nullable for events that happen before a client is assigned — e.g.
    # an invoice uploaded without client_id. These are still valuable in
    # portfolio-wide views but filtered out of per-client timelines.
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # When the event logically happened (may differ slightly from created_at
    # for back-dated / imported events; defaults to now at insert time).
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Free-form payload. Keep it small: identifiers and a short human-
    # readable summary. Big blobs should stay in the underlying tables;
    # the timeline renders links to them.
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Related entity (optional). Convenient for click-through from the
    # timeline row to the underlying object (invoice, rule execution, ...).
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Who
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped[Organization] = relationship()
    client: Mapped[Client | None] = relationship()
    actor: Mapped[User | None] = relationship()

    __table_args__ = (
        Index("ix_client_events_org_id", "organization_id"),
        Index("ix_client_events_client_id", "client_id"),
        # Primary access pattern: timeline for one client ordered by date desc
        Index("ix_client_events_client_date", "client_id", "event_date"),
        # Secondary: agency-wide views (portfolio, cross-client inbox)
        Index("ix_client_events_org_date", "organization_id", "event_date"),
    )
