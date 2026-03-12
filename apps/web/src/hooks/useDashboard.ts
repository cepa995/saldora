'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchInvoices } from '@/lib/api/invoices';
import { fetchDashboardStats } from '@/lib/api/dashboard';
import { useClient } from '@/contexts/ClientContext';
import type { InvoiceResponse } from '@/lib/types/invoice';
import type { MonthlyVolume, StatusCount, MonthlyTotal } from '@/lib/api/dashboard';

interface DashboardData {
  totalCount: number;
  processingCount: number;
  reviewCount: number;
  verifiedCount: number;
  exportedCount: number;
  recentInvoices: InvoiceResponse[];
  monthlyVolume: MonthlyVolume[];
  statusDistribution: StatusCount[];
  monthlyTotals: MonthlyTotal[];
}

interface UseDashboardReturn {
  data: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches dashboard summary data: status counts, recent invoices, and chart data.
 *
 * Runs 6 parallel API calls on mount:
 * 1. Recent invoices (last 5) + total count
 * 2-5. Per-status counts via filtered queries
 * 6. Dashboard analytics (monthly volume, status distribution, monthly totals)
 *
 * Returns:
 *   data - Dashboard stats, chart data, and recent invoices, or null while loading.
 *   isLoading - True during initial fetch or refresh.
 *   error - Error message if any call failed, or null.
 *   refresh - Function to re-trigger all fetches.
 */
export function useDashboard(): UseDashboardReturn {
  const { selectedClientId } = useClient();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setIsLoading(true);
      setError(null);

      try {
        const base = selectedClientId ? { client_id: selectedClientId } : {};
        const [
          recentResult,
          processingResult,
          reviewResult,
          verifiedResult,
          exportedResult,
          statsResult,
        ] = await Promise.all([
          fetchInvoices({ ...base, per_page: 5, sort: 'created_at', order: 'desc' }),
          fetchInvoices({ ...base, status: 'processing', per_page: 1 }),
          fetchInvoices({ ...base, status: 'review', per_page: 1 }),
          fetchInvoices({ ...base, status: 'verified', per_page: 1 }),
          fetchInvoices({ ...base, status: 'exported', per_page: 1 }),
          fetchDashboardStats(selectedClientId || undefined),
        ]);

        if (cancelled) return;

        setData({
          totalCount: recentResult.pagination.total,
          processingCount: processingResult.pagination.total,
          reviewCount: reviewResult.pagination.total,
          verifiedCount: verifiedResult.pagination.total,
          exportedCount: exportedResult.pagination.total,
          recentInvoices: recentResult.data,
          monthlyVolume: statsResult.monthly_volume,
          statusDistribution: statsResult.status_distribution,
          monthlyTotals: statsResult.monthly_totals,
        });
      } catch (err) {
        if (cancelled) return;
        const message =
          err && typeof err === 'object' && 'message' in err
            ? String(err.message)
            : 'Greška pri učitavanju podataka';
        setError(message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [refreshKey, selectedClientId]);

  return { data, isLoading, error, refresh };
}
