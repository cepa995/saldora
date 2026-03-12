"""Dashboard analytics response schemas."""

from pydantic import BaseModel


class MonthlyVolume(BaseModel):
    """Invoice count for a single month.

    Attributes:
        month: Period string in YYYY-MM format.
        count: Number of invoices in that month.
    """

    month: str
    count: int


class StatusCount(BaseModel):
    """Invoice count for a single status.

    Attributes:
        status: Invoice status (processing, review, verified, exported, error).
        count: Number of invoices with that status.
    """

    status: str
    count: int


class MonthlyTotal(BaseModel):
    """Total invoice amount for a single month.

    Attributes:
        month: Period string in YYYY-MM format.
        total_rsd: Sum of invoice amounts in RSD.
    """

    month: str
    total_rsd: float


class DashboardStatsResponse(BaseModel):
    """Aggregated dashboard statistics for charts.

    Attributes:
        monthly_volume: Invoice counts per month (last 12 months).
        status_distribution: Invoice counts per status.
        monthly_totals: Total RSD amounts per month (last 12 months).
    """

    monthly_volume: list[MonthlyVolume]
    status_distribution: list[StatusCount]
    monthly_totals: list[MonthlyTotal]
