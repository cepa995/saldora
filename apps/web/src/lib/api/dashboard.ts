/**
 * Dashboard analytics API functions.
 */

import { apiClient } from '@/lib/api-client';

export interface MonthlyVolume {
  month: string;
  count: number;
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface MonthlyTotal {
  month: string;
  total_rsd: number;
}

export interface DashboardStatsResponse {
  monthly_volume: MonthlyVolume[];
  status_distribution: StatusCount[];
  monthly_totals: MonthlyTotal[];
}

/**
 * Fetch aggregated dashboard statistics for charts.
 *
 * Args:
 *   clientId: Optional client ID filter for agency users.
 *
 * Returns:
 *   Dashboard chart data with monthly volume, status distribution,
 *   and monthly totals.
 */
export async function fetchDashboardStats(
  clientId?: string,
): Promise<DashboardStatsResponse> {
  const params = new URLSearchParams();
  if (clientId) params.set('client_id', clientId);
  const query = params.toString();
  const endpoint = query
    ? `/api/v1/analytics/dashboard?${query}`
    : '/api/v1/analytics/dashboard';
  return apiClient<DashboardStatsResponse>(endpoint);
}
