"""Plan definitions — single source of truth for all tier limits and features."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class PlanTier(StrEnum):
    """Valid plan tiers."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    AGENCY = "agency"


class Feature(StrEnum):
    """Gated features that require specific plan tiers."""

    OCR_EXTRACTION = "ocr_extraction"
    EXPORT_CSV_XLSX_JSON = "export_csv_xlsx_json"
    MINIMAX_XML_EXPORT = "minimax_xml_export"
    NBS_EXCHANGE_RATES = "nbs_exchange_rates"
    ACCOUNTING_INTENT = "accounting_intent"
    SEF_INTEGRATION = "sef_integration"
    MINIMAX_DIRECT_PUSH = "minimax_direct_push"
    AUTOMATION_RULES = "automation_rules"
    AUDIT_EXPORT = "audit_export"


@dataclass(frozen=True)
class PlanDefinition:
    """Immutable plan definition.

    Args:
        tier: Plan tier enum value.
        display_name: Human-readable plan name.
        price_monthly_eur: Monthly price in EUR, None for free tier.
        invoice_limit: Max invoices per month, None for unlimited.
        user_limit: Max users per organization, None for unlimited.
        overage_per_invoice_eur: Cost per invoice over the limit, None if no overage allowed.
        features: Set of features included in this plan.
    """

    tier: PlanTier
    display_name: str
    price_monthly_eur: Decimal | None
    invoice_limit: int | None
    user_limit: int | None
    overage_per_invoice_eur: Decimal | None
    features: frozenset[Feature] = field(default_factory=frozenset)


# Feature sets by tier level
_BASE_FEATURES: frozenset[Feature] = frozenset(
    {
        Feature.OCR_EXTRACTION,
        Feature.EXPORT_CSV_XLSX_JSON,
        Feature.MINIMAX_XML_EXPORT,
        Feature.NBS_EXCHANGE_RATES,
    }
)

_PRO_FEATURES: frozenset[Feature] = _BASE_FEATURES | frozenset(
    {
        Feature.ACCOUNTING_INTENT,
        Feature.SEF_INTEGRATION,
        Feature.MINIMAX_DIRECT_PUSH,
    }
)

_AGENCY_FEATURES: frozenset[Feature] = _PRO_FEATURES | frozenset(
    {
        Feature.AUTOMATION_RULES,
        Feature.AUDIT_EXPORT,
    }
)


PLANS: dict[PlanTier, PlanDefinition] = {
    PlanTier.FREE: PlanDefinition(
        tier=PlanTier.FREE,
        display_name="Free",
        price_monthly_eur=None,
        invoice_limit=10,
        user_limit=1,
        overage_per_invoice_eur=None,
        features=_BASE_FEATURES,
    ),
    PlanTier.STARTER: PlanDefinition(
        tier=PlanTier.STARTER,
        display_name="Starter",
        price_monthly_eur=Decimal("29"),
        invoice_limit=100,
        user_limit=2,
        overage_per_invoice_eur=Decimal("0.10"),
        features=_BASE_FEATURES,
    ),
    PlanTier.PRO: PlanDefinition(
        tier=PlanTier.PRO,
        display_name="Pro",
        price_monthly_eur=Decimal("79"),
        invoice_limit=400,
        user_limit=5,
        overage_per_invoice_eur=Decimal("0.07"),
        features=_PRO_FEATURES,
    ),
    PlanTier.AGENCY: PlanDefinition(
        tier=PlanTier.AGENCY,
        display_name="Agency",
        price_monthly_eur=Decimal("199"),
        invoice_limit=1500,
        user_limit=15,
        overage_per_invoice_eur=Decimal("0.05"),
        features=_AGENCY_FEATURES,
    ),
}


def get_plan(plan_name: str) -> PlanDefinition:
    """Look up a plan by its tier name string.

    Args:
        plan_name: Plan tier name (e.g. "free", "starter", "pro", "agency").

    Returns:
        The PlanDefinition for the given tier.

    Raises:
        ValueError: If the plan name is not recognized.
    """
    try:
        tier = PlanTier(plan_name)
    except ValueError:
        raise ValueError(f"Unknown plan: {plan_name}")
    return PLANS[tier]


def plan_has_feature(plan_name: str, feature: Feature) -> bool:
    """Check if a plan tier includes a specific feature.

    Args:
        plan_name: Plan tier name.
        feature: Feature to check.

    Returns:
        True if the plan includes the feature.
    """
    return feature in get_plan(plan_name).features
