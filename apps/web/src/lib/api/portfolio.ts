/**
 * Portfolio API helpers (M19.7).
 */

import { apiClient } from '@/lib/api-client';

export interface PortfolioMonthlyPoint {
  period: string; // YYYY-MM
  invoice_count: number;
  total_amount: string;
}

export interface PortfolioRow {
  client_id: string;
  name: string;
  pib: string;
  is_active: boolean;
  invoice_count: number;
  pending_review_count: number;
  blocked_count: number;
  /**
   * Overdue invoices for this client, right now — period-agnostic.
   * "Late regardless of which month you're browsing" is the semantic;
   * drops only when the invoice becomes exported (settled).
   */
  past_due_count: number;
  total_amount: string | null;
  last_activity_at: string | null;
  monthly_series: PortfolioMonthlyPoint[];
}

export interface PortfolioResponse {
  period: string;
  data: PortfolioRow[];
}

export async function fetchPortfolio(period?: string): Promise<PortfolioResponse> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : '';
  return apiClient<PortfolioResponse>(`/api/v1/portfolio${qs}`);
}
