"""Billing schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PlanInfo(BaseModel):
    """Plan tier information."""

    tier: str = Field(description="Plan tier: free, starter, pro, agency")
    display_name: str = Field(description="Human-readable plan name")
    price_monthly_eur: float | None = Field(description="Monthly price in EUR")
    invoice_limit: int | None = Field(description="Monthly invoice limit")
    user_limit: int | None = Field(description="Max users per organization")
    overage_per_invoice_eur: float | None = Field(description="Cost per invoice over the limit")
    features: list[str] = Field(description="Feature identifiers included in this plan")


class SubscriptionResponse(BaseModel):
    """Current subscription status and usage."""

    plan: str = Field(description="Current plan: free, starter, pro, agency")
    plan_limit: int | None = Field(description="Monthly invoice limit, null for unlimited")
    monthly_usage: int = Field(description="Invoices processed this month")
    organization_name: str = Field(description="Organization name")
    features: list[str] = Field(
        default_factory=list,
        description="Feature identifiers available on current plan",
    )
    subscription_status: str | None = Field(
        default=None,
        description="Subscription status: active, paused, past_due, canceled",
    )


class UsageResponse(BaseModel):
    """Current period usage details."""

    plan: PlanInfo = Field(description="Current plan details")
    period_start: date = Field(description="Billing period start date")
    period_end: date = Field(description="Billing period end date")
    invoices_used: int = Field(description="Invoices processed this period")
    invoices_limit: int | None = Field(description="Monthly invoice limit, null for unlimited")
    invoices_remaining: int | None = Field(
        description="Remaining invoices this period, null for unlimited"
    )
    api_calls: int = Field(description="API calls this period")
    storage_bytes: int = Field(description="Storage used this period in bytes")
    organization_name: str = Field(description="Organization name")
