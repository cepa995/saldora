"""FastAPI dependencies for injection."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.database import get_db
from app.models.invitation import Invitation
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User
from app.plans import PLANS, Feature, PlanTier, get_plan

# This tells FastAPI to look for a Bearer token in the Authorization header.
# tokenUrl is for the Swagger UI login form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Role hierarchy: higher number = more permissions
ROLE_HIERARCHY: dict[str, int] = {
    "admin": 4,
    "manager": 3,
    "operator": 2,
    "viewer": 1,
}


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract the current user from the JWT token.

    This is the main auth dependency. Add it to any endpoint that
    requires authentication:

        @router.get("/invoices")
        async def list_invoices(user: User = Depends(get_current_user)):
            # user is guaranteed to be authenticated here
    """
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

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


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

        now = datetime.now(UTC)
        count_result = await db.execute(
            select(func.count())
            .select_from(Invoice)
            .where(
                Invoice.organization_id == user.organization_id,
                extract("year", Invoice.created_at) == now.year,
                extract("month", Invoice.created_at) == now.month,
            )
        )
        monthly_usage = count_result.scalar() or 0

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
