'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchInvoices } from '@/lib/api/invoices';
import type { InvoiceResponse } from '@/lib/types/invoice';

interface DashboardData {
  totalCount: number;
  processingCount: number;
  reviewCount: number;
  verifiedCount: number;
  exportedCount: number;
  recentInvoices: InvoiceResponse[];
}

interface UseDashboardReturn {
  data: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches dashboard summary data: status counts and recent invoices.
 *
 * Runs 5 parallel API calls on mount:
 * 1. Recent invoices (last 5) + total count
 * 2-5. Per-status counts via filtered queries
 *
 * Returns:
 *   data - Dashboard stats and recent invoices, or null while loading.
 *   isLoading - True during initial fetch or refresh.
 *   error - Error message if any call failed, or null.
 *   refresh - Function to re-trigger all fetches.
 */
export function useDashboard(): UseDashboardReturn {
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
        const [recentResult, processingResult, reviewResult, verifiedResult, exportedResult] =
          await Promise.all([
            fetchInvoices({ per_page: 5, sort: 'created_at', order: 'desc' }),
            fetchInvoices({ status: 'processing', per_page: 1 }),
            fetchInvoices({ status: 'review', per_page: 1 }),
            fetchInvoices({ status: 'verified', per_page: 1 }),
            fetchInvoices({ status: 'exported', per_page: 1 }),
          ]);

        if (cancelled) return;

        setData({
          totalCount: recentResult.pagination.total,
          processingCount: processingResult.pagination.total,
          reviewCount: reviewResult.pagination.total,
          verifiedCount: verifiedResult.pagination.total,
          exportedCount: exportedResult.pagination.total,
          recentInvoices: recentResult.data,
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
  }, [refreshKey]);

  return { data, isLoading, error, refresh };
}
