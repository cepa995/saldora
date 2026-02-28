"""Audit logs router - admin-only access to audit trail."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> AuditLogListResponse:
    """List audit logs for the current organization (admin only).

    Args:
        db: Database session.
        user: Authenticated user (must be admin).
        page: Page number (1-based).
        per_page: Items per page (1–100).
        entity_type: Filter by entity type (e.g. ``user``, ``invoice``).
        entity_id: Filter by specific entity UUID.
        user_id: Filter by acting user UUID.
        action: Filter by action (e.g. ``login_success``, ``invoice.create``).
        date_from: Filter logs on or after this datetime.
        date_to: Filter logs on or before this datetime.
        order: Sort direction for created_at (asc or desc).

    Returns:
        Paginated list of audit log entries.
    """
    # Admin-only access
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs",
        )

    # Multi-tenant isolation
    conditions = [AuditLog.organization_id == user.organization_id]

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if action:
        conditions.append(AuditLog.action == action)
    if date_from:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to:
        conditions.append(AuditLog.created_at <= date_to)

    # Count
    count_query = select(func.count()).select_from(select(AuditLog).where(*conditions).subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Query with sorting and pagination
    order_func = desc if order == "desc" else asc
    query = (
        select(AuditLog)
        .where(*conditions)
        .order_by(order_func(AuditLog.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    data = [AuditLogResponse.model_validate(log) for log in logs]

    return AuditLogListResponse(
        data=data,
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    )
