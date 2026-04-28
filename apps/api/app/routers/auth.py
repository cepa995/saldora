"""Authentication router - login, register, token refresh."""

import os
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.join_request import JoinRequest
from app.models.organization import Organization
from app.models.user import User
from app.routers.organizations import _generate_unique_slug
from app.schemas.auth import (
    CreateOrganizationRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
)
from app.security import (
    blacklist_token,
    clear_failed_logins,
    is_account_locked,
    limiter,
    record_failed_login,
)
from app.services import audit
from app.services.email import (
    send_admin_new_org_email,
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)


def _initial_subscription_status() -> str:
    """Return the subscription status to assign to a freshly created org.

    Production registrations land in "pending" so an admin must explicitly
    activate the account before usage. Test runs auto-approve to avoid
    re-wiring every fixture; the test fixture sets TESTING=1 before app
    import.
    """
    return "active" if os.environ.get("TESTING") == "1" else "pending"


router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account (without an organization).

    After registration, the user must create or join an organization
    via the /auth/create-organization or /join-requests endpoints.

    Args:
        user_data: Registration data (email, password, name).
        request: HTTP request for audit context.
        db: Database session.

    Returns:
        JWT tokens for the newly created user.
    """
    # 1. Check email uniqueness
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # 2. Create user without organization
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        organization_id=None,
        role="viewer",
    )
    db.add(user)
    await db.flush()

    # 3. Audit log
    await audit.log(
        db=db,
        action="user.register",
        request=request,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        new_values={"email": user.email},
    )

    await db.commit()
    await db.refresh(user)

    # 4. Issue tokens so user can proceed to org setup
    access_token = create_access_token(
        str(user.id),
        None,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        email_verified=False,
    )
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/create-organization", response_model=TokenResponse)
async def create_organization(
    body: CreateOrganizationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TokenResponse:
    """Create a new organization for a user who doesn't have one yet.

    The user becomes the admin of the new organization. Returns fresh
    tokens with the organization claim embedded.

    Args:
        body: Organization name and optional PIB.
        request: HTTP request for audit context.
        db: Database session.
        user: Authenticated user (must not already belong to an org).

    Returns:
        Fresh JWT tokens with organization_id claim.
    """
    if user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already belongs to an organization",
        )

    # Block if user has a pending join request
    pending = await db.execute(
        select(JoinRequest)
        .where(
            JoinRequest.user_id == user.id,
            JoinRequest.status == "pending",
        )
        .limit(1)
    )
    if pending.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have a pending join request. Cancel it before creating an organization.",
        )

    # Validate PIB if provided
    if body.pib:
        _validate_pib(body.pib)

    # Create organization. New orgs land in subscription_status="pending"
    # so they cannot use mutational app routes until an admin flips the
    # status to "active"/"trial" (see require_role in app.dependencies).
    initial_status = _initial_subscription_status()
    org_slug = await _generate_unique_slug(db, body.name)
    org = Organization(
        name=body.name,
        slug=org_slug,
        pib=body.pib,
        billing_email=user.email,
        subscription_status=initial_status,
    )
    db.add(org)
    await db.flush()

    # Assign user to org as admin
    user.organization_id = org.id
    user.role = "admin"
    await db.flush()

    # Audit
    await audit.log(
        db=db,
        action="organization.create",
        request=request,
        organization_id=org.id,
        user_id=user.id,
        entity_type="organization",
        entity_id=org.id,
        new_values={"name": body.name, "pib": body.pib},
    )

    await db.commit()

    # Send verification email now that user has an organization
    if not user.email_verified:
        verification_token = create_email_verification_token(str(user.id), user.email)
        verification_url = f"{settings.frontend_url}/verify-email?token={verification_token}"
        background_tasks.add_task(
            send_verification_email, user.email, user.first_name, verification_url
        )

    # Notify the admin mailbox so a human can approve the org. This is the
    # gate for our manual-payment flow (no card-on-file). No-op if
    # admin_email is not configured (e.g. local dev without Resend).
    if initial_status == "pending":
        background_tasks.add_task(
            send_admin_new_org_email,
            org.name,
            org.pib,
            user.email,
            user.first_name,
            user.last_name,
        )

    # Issue fresh tokens with org claim
    access_token = create_access_token(
        str(user.id),
        str(org.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role="admin",
        org_slug=org_slug,
        email_verified=user.email_verified,
        subscription_status=org.subscription_status,
    )
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return JWT tokens.

    Rate limited to 10 attempts per minute per IP. Account locks after
    5 failed attempts for 15 minutes.

    Args:
        request: HTTP request for audit context and rate limiting.
        form_data: OAuth2 login credentials.
        db: Database session.

    Returns:
        JWT access and refresh tokens.
    """
    # 0. Check account lockout
    if await is_account_locked(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Previše neuspešnih pokušaja. Pokušajte ponovo za 15 minuta.",
        )

    # 1. Find user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # 2. Verify password (constant-time comparison to prevent timing attacks)
    if not user or not verify_password(form_data.password, user.password_hash):
        await record_failed_login(form_data.username)
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

    # 3. Clear lockout counter and audit successful login
    await clear_failed_logins(form_data.username)
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
    org_id = str(user.organization_id) if user.organization_id else None
    org_slug = None
    org_subscription_status: str | None = None
    if user.organization_id:
        org_row = await db.execute(
            select(Organization.slug, Organization.subscription_status).where(
                Organization.id == user.organization_id
            )
        )
        row = org_row.first()
        if row is not None:
            org_slug = row[0]
            org_subscription_status = row[1]
    access_token = create_access_token(
        str(user.id),
        org_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        org_slug=org_slug,
        email_verified=user.email_verified,
        subscription_status=org_subscription_status,
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
    """Refresh access token using refresh token.

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

    # 5. Issue new token pair (rotation). Re-read the org's subscription
    # status so a freshly approved customer picks up the new claim on
    # their next refresh — this is what the /awaiting-approval page polls.
    org_id = str(user.organization_id) if user.organization_id else None
    org_slug = None
    org_subscription_status: str | None = None
    if user.organization_id:
        org_row = await db.execute(
            select(Organization.slug, Organization.subscription_status).where(
                Organization.id == user.organization_id
            )
        )
        row = org_row.first()
        if row is not None:
            org_slug = row[0]
            org_subscription_status = row[1]
    access_token = create_access_token(
        str(user.id),
        org_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        org_slug=org_slug,
        email_verified=user.email_verified,
        subscription_status=org_subscription_status,
    )
    new_refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Logout user and blacklist the current access token.

    The token is added to a Redis blacklist for the remainder of its
    TTL, preventing reuse after logout.

    Args:
        request: HTTP request containing the Authorization header.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Confirmation message.
    """
    # Extract and blacklist the access token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                import time

                ttl = max(int(exp - time.time()), 0)
                if ttl > 0:
                    await blacklist_token(jti, ttl)
        except JWTError:
            pass  # Token already invalid, nothing to blacklist

    await audit.log(
        db=db,
        action="logout",
        request=request,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        entity_type="user",
        entity_id=current_user.id,
    )
    await db.commit()

    return {"message": "Logged out successfully"}


def _validate_pib(pib: str) -> None:
    """Validate Serbian PIB format using ISO 7064 Mod 11,10 checksum.

    Args:
        pib: PIB string to validate.

    Raises:
        HTTPException: If PIB is invalid.
    """
    cleaned = re.sub(r"[\s\-./]", "", pib.strip())

    if not cleaned.isdigit():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIB must contain only digits")

    if len(cleaned) != 9:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIB must be exactly 9 digits")

    if cleaned[0] == "0":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIB cannot start with 0")

    # Mod 11,10 checksum
    product = 10
    for i in range(8):
        s = (product + int(cleaned[i])) % 10
        if s == 0:
            s = 10
        product = (s * 2) % 11
    check_digit = (11 - product) % 10

    if int(cleaned[8]) != check_digit:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIB is not valid (check digit)")


@router.post("/password-reset/request")
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Request a password reset email.

    Always returns the same response regardless of whether the email
    exists, to prevent email enumeration.

    Args:
        body: Contains the email address.
        background_tasks: FastAPI background tasks for non-blocking email.
        db: Database session.

    Returns:
        Generic confirmation message.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        token = create_password_reset_token(str(user.id), user.email)
        reset_url = f"{settings.frontend_url}/password-reset/confirm?token={token}"
        background_tasks.add_task(send_password_reset_email, user.email, reset_url)

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Confirm password reset using the token from the email link.

    Validates the JWT reset token, updates the user's password,
    and logs the action.

    Args:
        body: Contains the reset token and new password.
        request: HTTP request for audit context.
        db: Database session.

    Returns:
        Success confirmation message.
    """
    # 1. Decode and validate the reset token
    try:
        payload = decode_token(body.token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )

    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )

    # 2. Find the user
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )

    # 3. Update password
    user.password_hash = hash_password(body.new_password)

    # 4. Audit log
    await audit.log(
        db=db,
        action="password_reset",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )

    await db.commit()

    return {"message": "Password has been reset successfully"}


@router.get("/verify")
async def verify_email(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Verify a user's email address using the token from the verification link.

    Args:
        token: JWT verification token from the email link.
        request: HTTP request for audit context.
        db: Database session.

    Returns:
        Success confirmation message.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link za verifikaciju je nevažeći ili je istekao",
        )

    if payload.get("type") != "email_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nevažeći tip tokena",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link za verifikaciju je nevažeći ili je istekao",
        )

    if user.email_verified:
        return {"message": "Email je već verifikovan"}

    user.email_verified = True

    await audit.log(
        db=db,
        action="email.verified",
        request=request,
        organization_id=user.organization_id,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )

    # Send welcome email now that verification is complete
    background_tasks = BackgroundTasks()
    background_tasks.add_task(send_welcome_email, user.email, user.first_name)

    await db.commit()

    return {"message": "Email uspešno verifikovan"}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Resend the email verification link.

    Rate limited to 3 requests per minute.

    Args:
        request: HTTP request for rate limiting.
        background_tasks: FastAPI background tasks.
        db: Database session.
        user: Authenticated user.

    Returns:
        Confirmation message.
    """
    if user.email_verified:
        return {"message": "Email je već verifikovan"}

    verification_token = create_email_verification_token(str(user.id), user.email)
    verification_url = f"{settings.frontend_url}/verify-email?token={verification_token}"
    background_tasks.add_task(
        send_verification_email, user.email, user.first_name, verification_url
    )

    return {"message": "Verifikacioni email je ponovo poslat"}
