/**
 * Portfolio API helpers (M19.7).
 */

import { apiClient } from '@/lib/api-client';

export interface PortfolioRow {
  client_id: string;
  name: string;
  pib: string;
  is_active: boolean;
  invoice_count: number;
  pending_review_count: number;
  blocked_count: number;
  last_activity_at: string | null;
}

export interface PortfolioResponse {
  period: string;
  data: PortfolioRow[];
}

export async function fetchPortfolio(period?: string): Promise<PortfolioResponse> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : '';
  return apiClient<PortfolioResponse>(`/api/v1/portfolio${qs}`);
}
