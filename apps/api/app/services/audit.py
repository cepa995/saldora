"""Audit logging service.

Provides a single ``log()`` function that creates an AuditLog record
within the caller's existing database session. The caller controls
when to commit — the audit entry lives in the same transaction as
the business operation it records.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.audit_log import AuditLog


async def log(
    *,
    db: AsyncSession,
    action: str,
    request: Request | None = None,
    organization_id: UUID | None = None,
    user_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> AuditLog:
    """Create an audit log entry in the current transaction.

    Args:
        db: Async database session (caller manages commit/rollback).
        action: Short action identifier (e.g. ``login_success``, ``invoice.create``).
        request: HTTP request (used to extract IP and User-Agent from state).
        organization_id: Organization scope (nullable for failed logins).
        user_id: Acting user (nullable for failed logins).
        entity_type: Type of entity affected (e.g. ``user``, ``invoice``).
        entity_id: ID of the affected entity.
        old_values: Snapshot of fields before mutation.
        new_values: Snapshot of fields after mutation or context data.

    Returns:
        The newly created AuditLog instance (not yet committed).
    """
    ip_address = None
    user_agent = None
    if request is not None:
        ip_address = getattr(request.state, "ip_address", None)
        user_agent = getattr(request.state, "user_agent", None)

    entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    return entry
