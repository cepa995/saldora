/**
 * Reports API service functions.
 *
 * Typed wrappers around apiClient for report template endpoints.
 */

import { apiClient } from '@/lib/api-client';

// ── Shared filter params ─────────────────────────────────────────────

export interface ReportParams {
  date_from?: string;
  date_to?: string;
  seller_pib?: string;
  description?: string;
}

function buildQuery(params: ReportParams): string {
  const qs = new URLSearchParams();
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.seller_pib) qs.set('seller_pib', params.seller_pib);
  if (params.description) qs.set('description', params.description);
  const str = qs.toString();
  return str ? `?${str}` : '';
}

// ── 1. Received goods ────────────────────────────────────────────────

export interface ReceivedGoodsItem {
  description: string;
  total_quantity: number | null;
  total_amount: number;
  avg_unit_price: number | null;
  supplier_count: number;
  suppliers: string[];
}

export interface ReceivedGoodsResponse {
  items: ReceivedGoodsItem[];
  grand_total: number;
  item_count: number;
}

/**
 * Fetch received goods report grouped by description.
 *
 * @param params - Filter parameters.
 * @returns Grouped received goods data.
 */
export async function fetchReceivedGoods(
  params: ReportParams,
): Promise<ReceivedGoodsResponse> {
  return apiClient<ReceivedGoodsResponse>(
    `/api/v1/reports/received-goods${buildQuery(params)}`,
  );
}

// ── 2. Spending by supplier ──────────────────────────────────────────

export interface SpendingBySupplierItem {
  seller_name: string | null;
  seller_pib: string | null;
  total_amount: number;
  invoice_count: number;
}

export interface SpendingBySupplierResponse {
  items: SpendingBySupplierItem[];
  grand_total: number;
}

/**
 * Fetch spending grouped by supplier.
 *
 * @param params - Filter parameters.
 * @returns Spending per supplier.
 */
export async function fetchSpendingBySupplier(
  params: ReportParams,
): Promise<SpendingBySupplierResponse> {
  return apiClient<SpendingBySupplierResponse>(
    `/api/v1/reports/spending-by-supplier${buildQuery(params)}`,
  );
}

// ── 3. Monthly breakdown ─────────────────────────────────────────────

export interface MonthlyBreakdownItem {
  invoice_date: string | null;
  invoice_number: string | null;
  seller_name: string | null;
  seller_pib: string | null;
  description: string;
  quantity: number | null;
  unit_price: number | null;
  total: number;
}

export interface MonthlyBreakdownResponse {
  items: MonthlyBreakdownItem[];
  total_amount: number;
  item_count: number;
}

/**
 * Fetch all line items for the selected period.
 *
 * @param params - Filter parameters.
 * @returns All line items for the period.
 */
export async function fetchMonthlyBreakdown(
  params: ReportParams,
): Promise<MonthlyBreakdownResponse> {
  return apiClient<MonthlyBreakdownResponse>(
    `/api/v1/reports/monthly-breakdown${buildQuery(params)}`,
  );
}

// ── 4. Price comparison ──────────────────────────────────────────────

export interface PriceComparisonItem {
  description: string;
  supplier_prices: {
    seller_name: string | null;
    seller_pib: string | null;
    min_price: number;
    max_price: number;
    avg_price: number;
    occurrence_count: number;
  }[];
  global_min: number;
  global_max: number;
  global_avg: number;
}

export interface PriceComparisonResponse {
  items: PriceComparisonItem[];
}

/**
 * Fetch price comparison for the same items across different suppliers.
 *
 * @param params - Filter parameters.
 * @returns Price comparison data.
 */
export async function fetchPriceComparison(
  params: ReportParams,
): Promise<PriceComparisonResponse> {
  return apiClient<PriceComparisonResponse>(
    `/api/v1/reports/price-comparison${buildQuery(params)}`,
  );
}

// ── 5. Expense summary ───────────────────────────────────────────────

export interface ExpenseSummaryItem {
  period: string;
  invoice_count: number;
  total_amount: number;
  seller_count: number;
}

export interface ExpenseSummaryResponse {
  items: ExpenseSummaryItem[];
  grand_total: number;
}

/**
 * Fetch expenses grouped by month.
 *
 * @param params - Filter parameters.
 * @returns Monthly expense summary.
 */
export async function fetchExpenseSummary(
  params: ReportParams,
): Promise<ExpenseSummaryResponse> {
  return apiClient<ExpenseSummaryResponse>(
    `/api/v1/reports/expense-summary${buildQuery(params)}`,
  );
}

// ── 6. Kalkulacija prodajne cene ─────────────────────────────────────

export interface KalkulacijaItem {
  description: string;
  unit_of_measure: string | null;
  quantity: number | null;
  purchase_price: number | null;
  purchase_value: number | null;
  margin_pct: number | null;
  margin_amount: number | null;
  tax_rate: number | null;
  tax_amount: number | null;
  selling_price: number | null;
  selling_value: number | null;
  supplier_name: string | null;
  invoice_date: string | null;
}

export interface KalkulacijaResponse {
  items: KalkulacijaItem[];
  total_purchase_value: number;
  total_selling_value: number;
  total_margin: number;
  item_count: number;
}

/**
 * Fetch selling price calculation report.
 *
 * @param params - Filter parameters.
 * @returns Kalkulacija data with purchase, margin and selling prices.
 */
export async function fetchKalkulacija(
  params: ReportParams,
): Promise<KalkulacijaResponse> {
  return apiClient<KalkulacijaResponse>(
    `/api/v1/reports/kalkulacija${buildQuery(params)}`,
  );
}

// ── 7. Razlika u ceni (RUC) ──────────────────────────────────────────

export interface RucItem {
  description: string;
  category: string | null;
  avg_purchase_price: number | null;
  selling_price: number | null;
  ruc_amount: number | null;
  ruc_pct: number | null;
  total_purchased_qty: number | null;
  total_purchased_value: number | null;
  suppliers: string[];
}

export interface RucResponse {
  items: RucItem[];
  avg_margin_pct: number;
  total_purchase_value: number;
  item_count: number;
}

/**
 * Fetch RUC (razlika u ceni) margin analysis report.
 *
 * @param params - Filter parameters.
 * @returns RUC data with purchase vs. selling price margin per product.
 */
export async function fetchRuc(
  params: ReportParams,
): Promise<RucResponse> {
  return apiClient<RucResponse>(
    `/api/v1/reports/ruc${buildQuery(params)}`,
  );
}

// ── 8. DPU (Šank lista) ──────────────────────────────────────────────

export interface DpuItem {
  description: string;
  unit_of_measure: string | null;
  opening_stock: number;
  purchased: number;
  closing_stock: number | null;
  consumed: number | null;
  selling_price: number | null;
  revenue: number | null;
}

export interface DpuResponse {
  date: string;
  items: DpuItem[];
  total_purchased_value: number;
  total_revenue: number | null;
}

/**
 * Fetch DPU (Dnevni Promet Ugostitelja) report for a specific date.
 *
 * @param date - Date string in YYYY-MM-DD format.
 * @returns DPU data with items and totals.
 */
export async function fetchDpu(date: string): Promise<DpuResponse> {
  return apiClient<DpuResponse>(`/api/v1/reports/dpu?date=${date}`);
}

// ── 9. Spending by category ──────────────────────────────────────────

export interface CategorySpendingItem {
  category: string;
  total_amount: number;
  item_count: number;
  invoice_count: number;
}

export interface CategorySpendingResponse {
  items: CategorySpendingItem[];
  grand_total: number;
}

/**
 * Fetch spending grouped by product category.
 *
 * @param params - Filter parameters.
 * @returns Spending totals per category.
 */
export async function fetchCategorySpending(
  params: ReportParams,
): Promise<CategorySpendingResponse> {
  return apiClient<CategorySpendingResponse>(
    `/api/v1/reports/spending-by-category${buildQuery(params)}`,
  );
}
