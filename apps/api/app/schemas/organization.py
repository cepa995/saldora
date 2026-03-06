"""Pydantic schemas for organization settings."""

from pydantic import BaseModel, EmailStr, Field


class OrganizationResponse(BaseModel):
    """Response schema for organization details."""

    id: str = Field(description="Organization UUID")
    name: str = Field(description="Organization display name")
    slug: str = Field(description="URL-friendly organization identifier")
    pib: str | None = Field(default=None, description="Tax ID (PIB)")
    billing_email: str | None = Field(default=None, description="Email for billing notifications")
    plan: str = Field(description="Current subscription plan")
    settings: dict = Field(default_factory=dict, description="Organization-specific settings")

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    """Request schema for updating organization settings."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Organization name",
    )
    billing_email: EmailStr | None = Field(
        default=None,
        description="Email for billing notifications",
    )
    pib: str | None = Field(
        default=None,
        max_length=20,
        description="Tax ID (PIB)",
    )
    settings: dict | None = Field(
        default=None,
        description="Organization-specific settings",
    )
