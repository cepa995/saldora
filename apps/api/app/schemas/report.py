"""Pydantic v2 schemas for Saldora invoice report templates."""

from datetime import date

from pydantic import BaseModel


class ReportFilters(BaseModel):
    """Common filter parameters shared across all report endpoints.

    Attributes:
        date_from: Inclusive start date for filtering by invoice date.
        date_to: Inclusive end date for filtering by invoice date.
        seller_pib: Filter results to a specific supplier by PIB.
        search: Case-insensitive substring filter on line item description.
    """

    date_from: date | None = None
    date_to: date | None = None
    seller_pib: str | None = None
    search: str | None = None


# ---------------------------------------------------------------------------
# 1. Received Goods
# ---------------------------------------------------------------------------


class ReceivedGoodsItem(BaseModel):
    """Aggregated received-goods row grouped by line item description.

    Attributes:
        description: Line item description (group key).
        total_quantity: Sum of quantities across all matching line items.
        total_amount: Sum of totals across all matching line items.
        avg_unit_price: Average unit price across all matching line items.
        supplier_count: Number of distinct suppliers that delivered this item.
        suppliers: Deduplicated list of supplier names.
    """

    description: str
    total_quantity: float | None
    total_amount: float
    avg_unit_price: float | None
    supplier_count: int
    suppliers: list[str]


class ReceivedGoodsResponse(BaseModel):
    """Response envelope for the received-goods report.

    Attributes:
        items: List of aggregated rows ordered by total_amount descending.
        grand_total: Sum of total_amount across all rows.
        item_count: Number of distinct description groups returned.
    """

    items: list[ReceivedGoodsItem]
    grand_total: float
    item_count: int


# ---------------------------------------------------------------------------
# 2. Spending by Supplier
# ---------------------------------------------------------------------------


class SpendingBySupplierItem(BaseModel):
    """Aggregated spending row grouped by supplier.

    Attributes:
        seller_name: Supplier's legal name (may be None for unknown suppliers).
        seller_pib: Supplier's PIB tax identifier (may be None).
        total_amount: Sum of all line item totals for this supplier.
        invoice_count: Number of distinct invoices from this supplier.
    """

    seller_name: str | None
    seller_pib: str | None
    total_amount: float
    invoice_count: int


class SpendingBySupplierResponse(BaseModel):
    """Response envelope for the spending-by-supplier report.

    Attributes:
        items: List of aggregated rows ordered by total_amount descending.
        grand_total: Sum of total_amount across all rows.
    """

    items: list[SpendingBySupplierItem]
    grand_total: float


# ---------------------------------------------------------------------------
# 3. Monthly Breakdown
# ---------------------------------------------------------------------------


class MonthlyBreakdownItem(BaseModel):
    """Single line item row returned in the monthly breakdown report.

    Attributes:
        id: Line item UUID.
        invoice_id: Parent invoice UUID.
        description: Line item description.
        quantity: Quantity (may be None if not extracted).
        unit_price: Unit price (may be None if not extracted).
        total: Line item total amount.
        tax_rate: Applied tax rate percentage (may be None).
        seller_name: Supplier name (may be None).
        invoice_date: Invoice date as an ISO-8601 string (may be None).
    """

    id: str
    invoice_id: str
    description: str
    quantity: float | None
    unit_price: float | None
    total: float
    tax_rate: float | None
    tax_amount: float | None
    seller_name: str | None
    invoice_date: str | None


class MonthlyBreakdownResponse(BaseModel):
    """Paginated response envelope for the monthly breakdown report.

    Attributes:
        items: Page of line item rows ordered by invoice_date desc.
        total_amount: Sum of total across the full (unfiltered) result set.
        item_count: Total number of matching rows across all pages.
    """

    items: list[MonthlyBreakdownItem]
    total_amount: float
    item_count: int


# ---------------------------------------------------------------------------
# 4. Price Comparison
# ---------------------------------------------------------------------------


class PriceComparisonItem(BaseModel):
    """Aggregated price row grouped by description and supplier.

    Attributes:
        description: Line item description (group key).
        seller_name: Supplier name (may be None).
        seller_pib: Supplier PIB (may be None).
        avg_unit_price: Average unit price across matching line items.
        min_unit_price: Minimum unit price seen across matching line items.
        max_unit_price: Maximum unit price seen across matching line items.
        total_quantity: Sum of quantities across matching line items.
        invoice_count: Number of distinct invoices contributing to this row.
    """

    description: str
    seller_name: str | None
    seller_pib: str | None
    avg_unit_price: float | None
    min_unit_price: float | None
    max_unit_price: float | None
    total_quantity: float | None
    invoice_count: int


class PriceComparisonResponse(BaseModel):
    """Response envelope for the price comparison report.

    Attributes:
        items: List of aggregated rows ordered by description then avg_unit_price.
    """

    items: list[PriceComparisonItem]


# ---------------------------------------------------------------------------
# 5. Expense Summary
# ---------------------------------------------------------------------------


class ExpenseSummaryBucket(BaseModel):
    """Aggregated expense totals for a single time bucket.

    Attributes:
        period: Bucket start in YYYY-MM format (month) or YYYY-WNN (week).
        total_amount: Sum of line item totals within this period.
        item_count: Number of line items within this period.
    """

    period: str
    total_amount: float
    item_count: int


class ExpenseSummaryResponse(BaseModel):
    """Response envelope for the expense summary report.

    Attributes:
        buckets: List of period buckets ordered chronologically.
        grand_total: Sum of total_amount across all buckets.
    """

    buckets: list[ExpenseSummaryBucket]
    grand_total: float


# ---------------------------------------------------------------------------
# Restaurant-specific reports
# ---------------------------------------------------------------------------


class KalkulacijaItem(BaseModel):
    """Single item in a price calculation (kalkulacija) report.

    Attributes:
        description: Item description.
        unit_of_measure: Unit (kg, kom, l, etc).
        quantity: Purchased quantity.
        purchase_price: Nabavna cena (unit_price from invoice).
        purchase_value: Nabavna vrednost (qty * purchase_price).
        margin_pct: Configured margin percentage (from product_catalog).
        margin_amount: Calculated margin amount.
        tax_rate: PDV rate.
        tax_amount: PDV amount.
        selling_price: Prodajna cena sa PDV.
        selling_value: Prodajna vrednost.
        supplier_name: Which supplier this came from.
        invoice_number: Source invoice number.
        invoice_date: Source invoice date.
    """

    description: str
    unit_of_measure: str | None = None
    quantity: float | None = None
    purchase_price: float | None = None
    purchase_value: float | None = None
    margin_pct: float | None = None
    margin_amount: float | None = None
    tax_rate: float | None = None
    tax_amount: float | None = None
    selling_price: float | None = None
    selling_value: float | None = None
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None


class KalkulacijaResponse(BaseModel):
    """Response for the kalkulacija (price calculation) report."""

    items: list[KalkulacijaItem]
    total_purchase_value: float
    total_selling_value: float
    total_margin: float
    item_count: int


class RucItem(BaseModel):
    """Single item in a RUC (razlika u ceni) report.

    Attributes:
        description: Canonical product name.
        category: Product category (piće, hrana, etc).
        avg_purchase_price: Average nabavna cena across invoices.
        selling_price: Configured prodajna cena.
        ruc_amount: Razlika u ceni (selling - purchase).
        ruc_pct: Margin percentage.
        total_purchased_qty: Total quantity purchased in period.
        total_purchased_value: Total nabavna vrednost.
        suppliers: List of suppliers for this item.
    """

    description: str
    category: str | None = None
    avg_purchase_price: float | None = None
    selling_price: float | None = None
    ruc_amount: float | None = None
    ruc_pct: float | None = None
    total_purchased_qty: float | None = None
    total_purchased_value: float | None = None
    suppliers: list[str] = []


class RucResponse(BaseModel):
    """Response for the RUC (razlika u ceni) report."""

    items: list[RucItem]
    avg_margin_pct: float
    total_purchase_value: float
    item_count: int


class CategorySpendingItem(BaseModel):
    """Spending by product category.

    Attributes:
        category: Product category (piće, hrana, materijal, etc).
        total_amount: Total spend in this category.
        item_count: Number of distinct items.
        invoice_count: Number of invoices.
    """

    category: str
    total_amount: float
    item_count: int
    invoice_count: int


class CategorySpendingResponse(BaseModel):
    """Response for spending by category report."""

    items: list[CategorySpendingItem]
    grand_total: float


# ---------------------------------------------------------------------------
# Open Items (Otvorene stavke)
# ---------------------------------------------------------------------------


class OpenItemsRow(BaseModel):
    """A single unpaid or partially paid invoice row.

    Attributes:
        invoice_id: UUID of the invoice.
        invoice_number: Invoice number from OCR.
        invoice_date: Date of the invoice.
        due_date: Payment due date.
        seller_name: Supplier name.
        seller_pib: Supplier PIB.
        total_amount: Invoice total.
        paid_amount: Amount paid so far.
        remaining_amount: Unpaid balance.
        payment_status: 'unpaid' or 'partially_paid'.
        days_overdue: Days past due date (0 if not overdue).
        currency: Invoice currency.
    """

    invoice_id: str
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    seller_name: str | None
    seller_pib: str | None
    total_amount: float | None
    paid_amount: float
    remaining_amount: float
    payment_status: str
    days_overdue: int
    currency: str


class OpenItemsResponse(BaseModel):
    """Response for open items report.

    Attributes:
        items: List of open invoice rows.
        total_open_amount: Total remaining balance across all items.
        total_overdue_amount: Total remaining balance for overdue items only.
        count: Number of open items.
    """

    items: list[OpenItemsRow]
    total_open_amount: float
    total_overdue_amount: float
    count: int


# ---------------------------------------------------------------------------
# Aging Analysis (Analiza dospeća)
# ---------------------------------------------------------------------------


class AgingBucket(BaseModel):
    """A single aging bucket.

    Attributes:
        bucket: Label for the bucket (e.g. '0-30', '31-60', '61-90', '90+').
        count: Number of invoices in this bucket.
        total_amount: Total remaining amount in this bucket.
    """

    bucket: str
    count: int
    total_amount: float


class AgingResponse(BaseModel):
    """Response for aging analysis report.

    Attributes:
        buckets: List of aging buckets.
        grand_total: Total outstanding amount across all buckets.
        overdue_total: Total amount that is past due (excludes 0-30 current).
    """

    buckets: list[AgingBucket]
    grand_total: float
    overdue_total: float
