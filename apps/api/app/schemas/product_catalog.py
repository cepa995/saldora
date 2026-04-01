"""Pydantic schemas for the product catalog API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Create a canonical product entry."""

    canonical_name: str = Field(..., min_length=1, max_length=500)
    unit_of_measure: str | None = Field(None, max_length=20)
    category: str | None = Field(None, max_length=50)
    aliases: list[str] = Field(default_factory=list)
    selling_price: float | None = None
    default_margin_pct: float | None = None


class ProductUpdate(BaseModel):
    """Update a product entry (all fields optional)."""

    canonical_name: str | None = Field(None, min_length=1, max_length=500)
    unit_of_measure: str | None = None
    category: str | None = None
    aliases: list[str] | None = None
    selling_price: float | None = None
    default_margin_pct: float | None = None


class ProductResponse(BaseModel):
    """Product catalog entry response."""

    id: UUID
    organization_id: UUID
    canonical_name: str
    unit_of_measure: str | None
    category: str | None
    aliases: list[str]
    selling_price: float | None
    default_margin_pct: float | None
    match_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductMergeSuggestion(BaseModel):
    """Suggested merge of similar item descriptions into one product."""

    description_a: str
    description_b: str
    similarity: float  # 0.0 to 1.0
    supplier_a: str | None = None
    supplier_b: str | None = None
    suggested_canonical: str


class ProductMergeSuggestionList(BaseModel):
    """List of merge suggestions."""

    suggestions: list[ProductMergeSuggestion]
    total: int
