"""PDV book (KPR/KIR) generation schemas."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PdvBookRequest(BaseModel):
    """Request to generate a KPR or KIR book for a given period."""

    book_type: Literal["KPR", "KIR"] = Field(description="Book type: KPR or KIR")
    period: str = Field(description="Period in YYYY-MM format")
    format: Literal["xlsx", "csv"] = Field(default="xlsx", description="Export format: xlsx or csv")
    client_id: UUID | None = Field(default=None, description="Filter by client (agency only)")

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        """Validate period format is YYYY-MM."""
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise ValueError("Period mora biti u formatu YYYY-MM")
        return v


class PdvBookPreviewResponse(BaseModel):
    """Preview response with entry count for a period."""

    entry_count: int = Field(description="Number of entries in the period")
    period: str = Field(description="Period in YYYY-MM format")
    book_type: str = Field(description="Book type: KPR or KIR")
