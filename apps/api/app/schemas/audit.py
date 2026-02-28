"""Audit log schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Schema for a single audit log entry."""

    id: UUID
    organization_id: UUID | None
    user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: UUID | None
    old_values: dict | None
    new_values: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    data: list[AuditLogResponse]
    pagination: dict
