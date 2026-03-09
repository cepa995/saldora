"""Invitation management router."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.models.invitation import Invitation
from app.models.organization import Organization
from app.models.user import User
from app.schemas.invitation import (
    AcceptInvitationRequest,
    InvitationCreate,
    InvitationPublicInfo,
    InvitationResponse,
)
from app.services import audit
from app.services.email import send_invitation_email

router = APIRouter()

INVITATION_EXPIRY_DAYS = 7


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    body: InvitationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> InvitationResponse:
    """Create an invitation to join the organization.

    Only administrators can create invitations.

    Args:
        body: Invitation details (email, role).
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Created invitation with token.
    """
    # Check for existing pending invitation
    existing = await db.execute(
        select(Invitation).where(
            Invitation.organization_id == user.organization_id,
            Invitation.email == body.email,
            Invitation.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    # Check if user already exists in the organization
    existing_user = await db.execute(
        select(User).where(
            User.email == body.email,
            User.organization_id == user.organization_id,
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already a member of the organization",
        )

    invitation = Invitation(
        organization_id=user.organization_id,
        email=body.email,
        role=body.role,
        token=secrets.token_urlsafe(32),
        invited_by=user.id,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=INVITATION_EXPIRY_DAYS),
    )
    db.add(invitation)

    await audit.log(
        db=db,
        action="invitation.create",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invitation",
        entity_id=invitation.id,
        new_values={"email": body.email, "role": body.role},
    )
    await db.commit()
    await db.refresh(invitation)

    # Send invitation email
    settings = get_settings()
    accept_url = f"{settings.frontend_url}/invite/{invitation.token}"
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == user.organization_id)
    )
    org_name = org_result.scalar_one()
    inviter_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
    await send_invitation_email(
        to_email=body.email,
        organization_name=org_name,
        role=body.role,
        accept_url=accept_url,
        inviter_name=inviter_name,
    )

    return InvitationResponse.model_validate(invitation)


@router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> list[InvitationResponse]:
    """List pending invitations for the organization.

    Only administrators can view invitations.

    Args:
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        List of pending invitations.
    """
    result = await db.execute(
        select(Invitation)
        .where(
            Invitation.organization_id == user.organization_id,
            Invitation.status == "pending",
        )
        .order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()

    # Auto-expire overdue invitations
    now = datetime.now(UTC)
    for inv in invitations:
        if inv.expires_at < now:
            inv.status = "expired"
    await db.commit()

    return [
        InvitationResponse.model_validate(inv) for inv in invitations if inv.status == "pending"
    ]


@router.delete("/{invitation_id}", status_code=status.HTTP_200_OK)
async def revoke_invitation(
    invitation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Revoke a pending invitation.

    Only administrators can revoke invitations.

    Args:
        invitation_id: UUID of the invitation.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must be admin).

    Returns:
        Success message.
    """
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == user.organization_id,
            Invitation.status == "pending",
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    invitation.status = "revoked"

    await audit.log(
        db=db,
        action="invitation.revoke",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="invitation",
        entity_id=invitation.id,
        old_values={"status": "pending"},
        new_values={"status": "revoked"},
    )
    await db.commit()

    return {"message": "Invitation revoked"}


@router.get("/accept/{token}", response_model=InvitationPublicInfo)
async def get_invitation_info(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> InvitationPublicInfo:
    """Get public info about an invitation (no auth required).

    Used to display the invitation details before accepting.

    Args:
        token: Invitation token.
        db: Database session.

    Returns:
        Organization name, role, and expiration.
    """
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Invitation has been {invitation.status}",
        )

    if invitation.expires_at < datetime.now(UTC):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    org_result = await db.execute(
        select(Organization).where(Organization.id == invitation.organization_id)
    )
    org = org_result.scalar_one()

    return InvitationPublicInfo(
        organization_name=org.name,
        role=invitation.role,
        email=invitation.email,
        expires_at=invitation.expires_at,
    )


@router.post("/accept/{token}", status_code=status.HTTP_201_CREATED)
async def accept_invitation(
    token: str,
    body: AcceptInvitationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Accept an invitation and create/link user account.

    If a user with the invited email already exists, they are moved
    to the new organization. Otherwise, a new user is created.

    Args:
        token: Invitation token.
        body: New user details (name, password).
        request: HTTP request for audit context.
        db: Database session.

    Returns:
        Success message.
    """
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Invitation has been {invitation.status}",
        )

    if invitation.expires_at < datetime.now(UTC):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == invitation.email))
    existing_user = existing.scalar_one_or_none()

    if existing_user:
        # Check if already in the target org
        if existing_user.organization_id == invitation.organization_id:
            invitation.status = "accepted"
            await db.commit()
            return {"message": "You are already a member of this organization"}

        # Move user to new org with invited role
        existing_user.organization_id = invitation.organization_id
        existing_user.role = invitation.role
    else:
        # Create new user
        new_user = User(
            email=invitation.email,
            password_hash=hash_password(body.password),
            first_name=body.first_name or "",
            last_name=body.last_name or "",
            organization_id=invitation.organization_id,
            role=invitation.role,
        )
        db.add(new_user)

    invitation.status = "accepted"

    await audit.log(
        db=db,
        action="invitation.accept",
        request=request,
        organization_id=invitation.organization_id,
        entity_type="invitation",
        entity_id=invitation.id,
        new_values={
            "email": invitation.email,
            "role": invitation.role,
        },
    )
    await db.commit()

    return {"message": "Invitation accepted successfully"}
