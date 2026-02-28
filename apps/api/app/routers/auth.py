"""Authentication router - login, register, token refresh."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenResponse, UserCreate, UserResponse
from app.services import audit

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    API Endpoint for User Registration

    Arguments:
        user_data (UserCreate): registration data inserted by the user
        request (Request): HTTP request for audit context.
        db (AsyncSession): DB session which is being injected via get_db
        dependency

    Returns:
        Newly created user (User) model
    """
    # 1. Check email uniqueness
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # 2. Create organization
    org = Organization(
        name=user_data.organization_name or f"{user_data.email.split('@')[0]}'s organization"
    )
    db.add(org)
    await db.flush()  # Assigns org.id without committing

    # 3. Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        organization_id=org.id,
        role="admin",  # First user in org is admin
    )
    db.add(user)
    await db.flush()

    # 4. Audit log (same transaction)
    await audit.log(
        db=db,
        action="user.register",
        request=request,
        organization_id=org.id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        new_values={"email": user.email},
    )

    await db.commit()
    await db.refresh(user)  # Reload to get server-generated fields (id, created_at)

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    API Endpoint for User Authentication/Login

    Arguments:
        request (Request): HTTP request for audit context.
        form_data (OAuth2PasswordRequestForm): login data inserted by the user
        db (AsyncSession): DB session which is being injected via get_db
        dependency

    Returns:
        JWT token if the user exists, otherwise, exception is raised
    """
    # 1. Find user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # 2. Verify password (constant-time comparison to prevent timing attacks)
    if not user or not verify_password(form_data.password, user.password_hash):
        # Audit failed login before raising (separate commit — the main
        # transaction has nothing else to persist)
        await audit.log(
            db=db,
            action="login_failure",
            request=request,
            new_values={"email": form_data.username},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # 3. Audit successful login
    await audit.log(
        db=db,
        action="login_success",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()

    # 4. Generate tokens
    access_token = create_access_token(
        str(user.id),
        str(user.organization_id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Validates the refresh JWT, looks up the user, and issues
    a new access + refresh token pair (token rotation).
    """
    # 1. Decode and validate the refresh token
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # 2. Verify it is actually a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # 3. Look up the user to get current claims
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # 4. Audit token refresh
    await audit.log(
        db=db,
        action="token_refresh",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()

    # 5. Issue new token pair (rotation)
    access_token = create_access_token(
        str(user.id),
        str(user.organization_id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )
    new_refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout() -> dict[str, str]:
    """
    Logout user and invalidate tokens.
    """
    # TODO: Implement logout
    # 1. Add refresh token to blacklist
    # 2. Clear session
    return {"message": "Logged out successfully"}


@router.post("/password-reset/request")
async def request_password_reset(email: str) -> dict[str, str]:
    """
    Request password reset email.
    """
    # TODO: Implement password reset request
    # 1. Find user by email
    # 2. Generate reset token
    # 3. Send reset email
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(token: str, new_password: str) -> dict[str, str]:
    """
    Confirm password reset with token.
    """
    # TODO: Implement password reset confirmation
    # 1. Validate reset token
    # 2. Hash new password
    # 3. Update user password
    # 4. Invalidate all existing sessions
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not yet implemented",
    )
