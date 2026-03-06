"""Billing schemas."""

from pydantic import BaseModel, Field


class SubscriptionResponse(BaseModel):
    """Current subscription status and usage."""

    plan: str = Field(description="Current plan: free, starter, professional, enterprise")
    plan_limit: int | None = Field(description="Monthly invoice limit, null for unlimited")
    monthly_usage: int = Field(description="Invoices processed this month")
    organization_name: str = Field(description="Organization name")
