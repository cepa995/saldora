"""Pydantic schemas for ClientEvent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Event types exposed on the API surface. Keep aligned with constants in
# ``app.services.events``.
EventType = Literal[
    "invoice_uploaded",
    "invoice_verified",
    "invoice_exported",
    "accounting_intent_classified",
    "rule_fired",
    "client_assigned",
]


class ClientEventResponse(BaseModel):
    """A single timeline event."""

    id: UUID
    organization_id: UUID
    client_id: UUID | None
    event_type: str
    event_date: datetime
    payload: dict
    entity_type: str | None
    entity_id: UUID | None
    actor_user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientEventListResponse(BaseModel):
    """Paginated list of client events."""

    data: list[ClientEventResponse]
    pagination: dict
