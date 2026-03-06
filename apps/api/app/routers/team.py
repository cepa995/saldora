"""Team member management router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.team import TeamMemberResponse, UpdateMemberRoleRequest
from app.services import audit

router = APIRouter()

VALID_ROLES = {"admin", "manager", "operator", "viewer"}


@router.get("/members", response_model=list[TeamMemberResponse])
async def list_members(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TeamMemberResponse]:
    """List all members of the current organization.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        List of team members with their roles.
    """
    result = await db.execute(
        select(User).where(User.organization_id == user.organization_id).order_by(User.created_at)
    )
    members = result.scalars().all()
    return [TeamMemberResponse.model_validate(m) for m in members]


@router.patch(
    "/members/{user_id}/role",
    response_model=TeamMemberResponse,
)
async def update_member_role(
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TeamMemberResponse:
    """Update a team member's role.

    Only administrators can change roles.

    Args:
        user_id: UUID of the member to update.
        body: New role assignment.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Updated team member details.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change member roles",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == user.organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if member.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    old_role = member.role
    if old_role == body.role:
        return TeamMemberResponse.model_validate(member)

    member.role = body.role

    await audit.log(
        db=db,
        action="team.member.role_change",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=member.id,
        old_values={"role": old_role},
        new_values={"role": body.role},
    )
    await db.commit()
    await db.refresh(member)

    return TeamMemberResponse.model_validate(member)


@router.delete("/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_member(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Remove a member from the organization.

    Only administrators can remove members. Admins cannot remove themselves.

    Args:
        user_id: UUID of the member to remove.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Success message.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can remove members",
        )

    if user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == user.organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    await audit.log(
        db=db,
        action="team.member.remove",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=member.id,
        old_values={
            "email": member.email,
            "role": member.role,
        },
    )
    await db.delete(member)
    await db.commit()

    return {"message": "Member removed successfully"}
