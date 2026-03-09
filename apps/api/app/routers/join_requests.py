"""Join request management router."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.join_request import JoinRequest
from app.models.organization import Organization
from app.models.user import User
from app.schemas.join_request import (
    JoinRequestCreate,
    JoinRequestResponse,
    OrganizationSearchResult,
)
from app.services import audit

router = APIRouter()


@router.get(
    "/organizations/search",
    response_model=list[OrganizationSearchResult],
)
async def search_organizations(
    q: str = Query(min_length=3, description="Search query (min 3 characters)"),
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationSearchResult]:
    """Search organizations by name (public, no auth required).

    Returns only name and slug — no sensitive information.

    Args:
        q: Search query string.
        db: Database session.

    Returns:
        List of matching organizations (max 10).
    """
    result = await db.execute(
        select(Organization)
        .where(func.lower(Organization.name).contains(q.lower()))
        .order_by(Organization.name)
        .limit(10)
    )
    orgs = result.scalars().all()
    return [OrganizationSearchResult(id=org.id, name=org.name, slug=org.slug) for org in orgs]


@router.get("/mine", response_model=JoinRequestResponse | None)
async def get_my_pending_request(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JoinRequestResponse | None:
    """Get the current user's pending join request, if any.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        Pending join request or null.
    """
    result = await db.execute(
        select(JoinRequest, Organization)
        .join(Organization, JoinRequest.organization_id == Organization.id)
        .where(
            JoinRequest.user_id == user.id,
            JoinRequest.status == "pending",
        )
        .order_by(JoinRequest.created_at.desc())
        .limit(1)
    )
    row = result.first()
    if not row:
        return None

    jr, org = row
    return JoinRequestResponse(
        id=jr.id,
        organization_id=jr.organization_id,
        user_id=jr.user_id,
        message=jr.message,
        status=jr.status,
        reviewed_by=jr.reviewed_by,
        reviewed_at=jr.reviewed_at,
        created_at=jr.created_at,
        user_email=user.email,
        user_name=f"{user.first_name} {user.last_name}".strip() or None,
        organization_name=org.name,
    )


@router.post(
    "",
    response_model=JoinRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_join_request(
    body: JoinRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JoinRequestResponse:
    """Submit a request to join an organization.

    Args:
        body: Join request details (organization_id, optional message).
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.

    Returns:
        Created join request.
    """
    # Verify target org exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == body.organization_id)
    )
    if not org_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check if already a member of any org
    if user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already belong to an organization",
        )

    # Check for any existing pending request (not just to this org)
    existing = await db.execute(
        select(JoinRequest).where(
            JoinRequest.user_id == user.id,
            JoinRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending request for this organization",
        )

    join_req = JoinRequest(
        organization_id=body.organization_id,
        user_id=user.id,
        message=body.message,
        status="pending",
    )
    db.add(join_req)

    await audit.log(
        db=db,
        action="join_request.create",
        request=request,
        organization_id=body.organization_id,
        user_id=user.id,
        entity_type="join_request",
        entity_id=join_req.id,
    )
    await db.commit()
    await db.refresh(join_req)

    return JoinRequestResponse(
        id=join_req.id,
        organization_id=join_req.organization_id,
        user_id=join_req.user_id,
        message=join_req.message,
        status=join_req.status,
        reviewed_by=join_req.reviewed_by,
        reviewed_at=join_req.reviewed_at,
        created_at=join_req.created_at,
        user_email=user.email,
        user_name=f"{user.first_name} {user.last_name}".strip() or None,
    )


@router.get("/pending-count")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict[str, int]:
    """Get the number of pending join requests for the organization.

    Args:
        db: Database session.
        user: Authenticated admin user.

    Returns:
        Count of pending join requests.
    """
    result = await db.execute(
        select(func.count())
        .select_from(JoinRequest)
        .where(
            JoinRequest.organization_id == user.organization_id,
            JoinRequest.status == "pending",
        )
    )
    count = result.scalar_one()
    return {"count": count}


@router.get("", response_model=list[JoinRequestResponse])
async def list_join_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> list[JoinRequestResponse]:
    """List pending join requests for the organization.

    Only administrators can view join requests.

    Args:
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        List of pending join requests with user details.
    """
    result = await db.execute(
        select(JoinRequest, User)
        .join(User, JoinRequest.user_id == User.id)
        .where(
            JoinRequest.organization_id == user.organization_id,
            JoinRequest.status == "pending",
        )
        .order_by(JoinRequest.created_at.desc())
    )
    rows = result.all()

    return [
        JoinRequestResponse(
            id=jr.id,
            organization_id=jr.organization_id,
            user_id=jr.user_id,
            message=jr.message,
            status=jr.status,
            reviewed_by=jr.reviewed_by,
            reviewed_at=jr.reviewed_at,
            created_at=jr.created_at,
            user_email=u.email,
            user_name=f"{u.first_name} {u.last_name}".strip() or None,
        )
        for jr, u in rows
    ]


@router.post("/{request_id}/approve", status_code=status.HTTP_200_OK)
async def approve_join_request(
    request_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Approve a join request.

    The requesting user is added to the organization with viewer role.

    Args:
        request_id: UUID of the join request.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Success message.
    """
    result = await db.execute(
        select(JoinRequest).where(
            JoinRequest.id == request_id,
            JoinRequest.organization_id == user.organization_id,
            JoinRequest.status == "pending",
        )
    )
    join_req = result.scalar_one_or_none()
    if not join_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Join request not found",
        )

    # Get the requesting user
    requester_result = await db.execute(select(User).where(User.id == join_req.user_id))
    requester = requester_result.scalar_one()

    # Move user to this organization
    requester.organization_id = user.organization_id
    requester.role = "viewer"

    # Update join request
    join_req.status = "approved"
    join_req.reviewed_by = user.id
    join_req.reviewed_at = datetime.now(UTC)

    await audit.log(
        db=db,
        action="join_request.approve",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="join_request",
        entity_id=join_req.id,
        new_values={
            "requester_email": requester.email,
            "role": "viewer",
        },
    )
    await db.commit()

    return {"message": "Join request approved"}


@router.post("/{request_id}/reject", status_code=status.HTTP_200_OK)
async def reject_join_request(
    request_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Reject a join request.

    Args:
        request_id: UUID of the join request.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Success message.
    """
    result = await db.execute(
        select(JoinRequest).where(
            JoinRequest.id == request_id,
            JoinRequest.organization_id == user.organization_id,
            JoinRequest.status == "pending",
        )
    )
    join_req = result.scalar_one_or_none()
    if not join_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Join request not found",
        )

    join_req.status = "rejected"
    join_req.reviewed_by = user.id
    join_req.reviewed_at = datetime.now(UTC)

    await audit.log(
        db=db,
        action="join_request.reject",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="join_request",
        entity_id=join_req.id,
    )
    await db.commit()

    return {"message": "Join request rejected"}
