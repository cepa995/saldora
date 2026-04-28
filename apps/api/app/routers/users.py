"""User profile and password management router."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import (
    PasswordChangeRequest,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services import audit

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Get the current user's profile, including the org's subscription
    status so the frontend can decide whether to route into the app or to
    the awaiting-approval page.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        User profile details.
    """
    subscription_status: str | None = None
    if user.organization_id is not None:
        sub_result = await db.execute(
            select(Organization.subscription_status).where(Organization.id == user.organization_id)
        )
        subscription_status = sub_result.scalar_one_or_none()

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        email_verified=user.email_verified,
        organization_id=user.organization_id,
        subscription_status=subscription_status,
        created_at=user.created_at,
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    body: UserProfileUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Update the current user's profile.

    Args:
        body: Fields to update (first_name, last_name).
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.

    Returns:
        Updated user profile.
    """
    old_values: dict = {}
    new_values: dict = {}
    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        old = getattr(user, field)
        if old != value:
            old_values[field] = old
            new_values[field] = value
            setattr(user, field, value)

    if new_values:
        await audit.log(
            db=db,
            action="user.profile.update",
            request=request,
            organization_id=user.organization_id,
            user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            old_values=old_values,
            new_values=new_values,
        )
        await db.commit()
        await db.refresh(user)

    return UserProfileResponse.model_validate(user)


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Change the current user's password.

    Requires the current password for verification.

    Args:
        body: Current and new password.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user.

    Returns:
        Success message.
    """
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(body.new_password)

    await audit.log(
        db=db,
        action="user.password.change",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()

    return {"message": "Password changed successfully"}
