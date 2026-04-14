"""FastAPI dependencies for injection."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token, verify_password
from app.database import get_db
from app.models.api_key import APIKey
from app.models.invitation import Invitation
from app.models.organization import Organization
from app.models.user import User
from app.plans import PLANS, Feature, PlanTier, get_plan

logger = logging.getLogger(__name__)

# This tells FastAPI to look for a Bearer token in the Authorization header.
# tokenUrl is for the Swagger UI login form.
# auto_error=False so we can fall back to API key when no Bearer token is present.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Role hierarchy: higher number = more permissions
ROLE_HIERARCHY: dict[str, int] = {
    "admin": 4,
    "manager": 3,
    "operator": 2,
    "viewer": 1,
}

API_KEY_PREFIX = "sk_live_"


async def _authenticate_via_api_key(
    api_key: str,
    db: AsyncSession,
) -> User:
    """Authenticate a request using an API key.

    Looks up the key by prefix, verifies the hash, checks active/expiry,
    updates last_used_at, and returns the associated user.

    Args:
        api_key: Full API key string (sk_live_...).
        db: Database session.

    Returns:
        The User who created the API key.

    Raises:
        HTTPException: 401 if key is invalid, revoked, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked API key",
    )

    if not api_key.startswith(API_KEY_PREFIX):
        raise credentials_exception

    # Extract prefix for DB lookup (first 8 chars after sk_live_)
    key_body = api_key[len(API_KEY_PREFIX) :]
    if len(key_body) < 8:
        raise credentials_exception
    prefix = key_body[:8]

    # Find active keys matching this prefix
    result = await db.execute(
        select(APIKey).where(and_(APIKey.key_prefix == prefix, APIKey.is_active.is_(True)))
    )
    candidates = list(result.scalars().all())

    # Verify hash against each candidate (usually just one)
    matched_key: APIKey | None = None
    for candidate in candidates:
        if verify_password(api_key, candidate.key_hash):
            matched_key = candidate
            break

    if matched_key is None:
        raise credentials_exception

    # Check expiration
    if matched_key.expires_at and matched_key.expires_at < datetime.now(UTC):
        raise credentials_exception

    # Update last_used_at (fire-and-forget, don't block the request)
    await db.execute(
        update(APIKey).where(APIKey.id == matched_key.id).values(last_used_at=datetime.now(UTC))
    )
    await db.commit()

    # Fetch the associated user
    user_result = await db.execute(select(User).where(User.id == matched_key.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract the current user from JWT token or API key.

    Checks in order:
    1. Authorization: Bearer <jwt> header (existing JWT flow)
    2. X-API-Key: sk_live_... header (API key flow)
    3. Neither → 401

    Args:
        request: HTTP request (for reading X-API-Key header).
        token: JWT token from Authorization header (optional).
        db: Database session.

    Returns:
        Authenticated User instance.
    """
    # Try JWT first
    if token:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            if user_id is None or token_type != "access":
                raise credentials_exception

            # Check token blacklist (logout invalidation)
            jti = payload.get("jti")
            if jti:
                from app.security import is_token_blacklisted

                if await is_token_blacklisted(jti):
                    raise credentials_exception
        except JWTError:
            raise credentials_exception

        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        return user

    # Try API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _authenticate_via_api_key(api_key, db)

    # Neither provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(minimum_role: str) -> Callable:
    """Create a dependency that enforces a minimum role level and org membership.

    Args:
        minimum_role: The minimum role required (admin, manager, operator, viewer).

    Returns:
        A FastAPI dependency that returns the authenticated user if they have
        sufficient permissions, otherwise raises 403.
    """
    min_level = ROLE_HIERARCHY[minimum_role]

    async def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User must belong to an organization",
            )
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role} role or higher",
            )
        return user

    return _check_role


class QuotaCheck(NamedTuple):
    """Result of an invoice quota check.

    Attributes:
        user: Authenticated user.
        monthly_usage: Number of invoices created this month.
        invoice_limit: Plan's monthly invoice limit (None = unlimited).
        plan_name: Current plan tier name.
    """

    user: User
    monthly_usage: int
    invoice_limit: int | None
    plan_name: str


def _min_plan_for_feature(feature: Feature) -> str:
    """Find the cheapest plan tier that includes a given feature.

    Args:
        feature: The feature to look up.

    Returns:
        Display name of the minimum required plan tier.
    """
    tier_order = [PlanTier.STARTER, PlanTier.PRO, PlanTier.AGENCY]
    for tier in tier_order:
        if feature in PLANS[tier].features:
            return PLANS[tier].display_name
    return "Agency"


_TIER_UPGRADE_PATH: dict[str, str] = {
    "free": "Starter",
    "starter": "Pro",
    "pro": "Agency",
}


def _next_plan_tier(current_plan: str) -> str:
    """Return the display name of the next plan tier above *current_plan*.

    Args:
        current_plan: Lowercase slug of the current plan (e.g. "free").

    Returns:
        Display name of the next tier, or "Agency" if already at top.
    """
    return _TIER_UPGRADE_PATH.get(current_plan, "Agency")


def require_feature(*features: Feature) -> Callable:
    """Create a dependency that enforces plan feature access.

    Args:
        features: One or more Feature enum values required.

    Returns:
        A FastAPI dependency that returns the authenticated user if their
        plan includes all required features, otherwise raises 403.
    """

    async def _check_feature(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Korisnik mora pripadati organizaciji",
            )

        result = await db.execute(
            select(Organization.plan).where(Organization.id == user.organization_id)
        )
        plan_name = result.scalar_one_or_none() or "free"
        plan_def = get_plan(plan_name)

        missing = [f for f in features if f not in plan_def.features]
        if missing:
            required_plan = _min_plan_for_feature(missing[0])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": (
                        f"Vaš plan ne uključuje ovu funkcionalnost. Potreban plan: {required_plan}."
                    ),
                    "code": "feature_unavailable",
                    "plan": plan_name,
                    "required_plan": required_plan,
                },
            )
        return user

    return _check_feature


def check_invoice_quota() -> Callable:
    """Create a dependency that checks the organization's monthly invoice quota.

    Returns:
        A FastAPI dependency that returns a QuotaCheck if within limits,
        or raises 402 if the free-tier limit is reached.
    """

    async def _check_quota(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> QuotaCheck:
        if user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Korisnik mora pripadati organizaciji",
            )

        result = await db.execute(
            select(Organization.plan).where(Organization.id == user.organization_id)
        )
        plan_name = result.scalar_one_or_none() or "free"
        plan_def = get_plan(plan_name)

        from app.models.usage_record import UsageRecord

        now = datetime.now(UTC)
        period_start = now.replace(day=1).date()

        usage_result = await db.execute(
            select(UsageRecord.invoices_count).where(
                UsageRecord.organization_id == user.organization_id,
                UsageRecord.period_start == period_start,
            )
        )
        monthly_usage = usage_result.scalar() or 0

        invoice_limit = plan_def.invoice_limit
        if invoice_limit is not None and monthly_usage >= invoice_limit:
            next_plan = _next_plan_tier(plan_name)
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "detail": (
                        f"Dostigli ste mesečni limit od {invoice_limit} faktura "
                        f"za {plan_def.display_name} plan. Nadogradite plan za nastavak."
                    ),
                    "code": "invoice_limit_exceeded",
                    "plan": plan_name,
                    "limit": invoice_limit,
                    "usage": monthly_usage,
                    "required_plan": next_plan,
                },
            )

        return QuotaCheck(
            user=user,
            monthly_usage=monthly_usage,
            invoice_limit=invoice_limit,
            plan_name=plan_name,
        )

    return _check_quota


def check_member_quota() -> Callable:
    """Create a dependency that checks the organization's member limit.

    Returns:
        A FastAPI dependency that returns the authenticated user if within
        the member limit, or raises 402 if at capacity.
    """

    async def _check_members(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Korisnik mora pripadati organizaciji",
            )

        result = await db.execute(
            select(Organization.plan).where(Organization.id == user.organization_id)
        )
        plan_name = result.scalar_one_or_none() or "free"
        plan_def = get_plan(plan_name)

        if plan_def.user_limit is None:
            return user

        # Count active members
        member_count_result = await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.organization_id == user.organization_id)
        )
        member_count = member_count_result.scalar() or 0

        # Count pending invitations
        pending_count_result = await db.execute(
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.organization_id == user.organization_id,
                Invitation.status == "pending",
            )
        )
        pending_count = pending_count_result.scalar() or 0

        total = member_count + pending_count
        if total >= plan_def.user_limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "detail": (
                        f"Dostigli ste limit od {plan_def.user_limit} korisnika "
                        f"za {plan_def.display_name} plan. Nadogradite plan za više korisnika."
                    ),
                    "code": "member_limit_exceeded",
                    "plan": plan_name,
                    "limit": plan_def.user_limit,
                    "usage": total,
                    "required_plan": "Starter" if plan_name == "free" else "Pro",
                },
            )

        return user

    return _check_members
