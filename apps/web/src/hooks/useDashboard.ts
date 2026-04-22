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
  unassignedCount: number;
  pastDueCount: number;
  /** Sum of total_amount across past-due invoices, in RSD (mixed currencies
   *  fall back to total_amount). Capped by per_page=100 — see useDashboard. */
  pastDueTotalRsd: number;
  /** Max days-late across past-due invoices (0 when there are none). */
  pastDueOldestDays: number;
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
          unassignedResult,
          pastDueResult,
          statsResult,
        ] = await Promise.all([
          fetchInvoices({ ...base, per_page: 5, sort: 'created_at', order: 'desc' }),
          fetchInvoices({ ...base, status: 'processing', per_page: 1 }),
          fetchInvoices({ ...base, status: 'review', per_page: 1 }),
          fetchInvoices({ ...base, status: 'verified', per_page: 1 }),
          fetchInvoices({ ...base, status: 'exported', per_page: 1 }),
          // Only meaningful when not already scoped to one client
          selectedClientId
            ? Promise.resolve({ pagination: { total: 0, page: 1, per_page: 1, total_pages: 0 }, data: [] })
            : fetchInvoices({ unassigned: true, per_page: 1 }),
          // per_page=100 so we can aggregate total_amount + oldest-days on the
          // client. Agencies with >100 past-due invoices at once would see
          // undercounts — unusual for the hospitality target; swap to a
          // backend aggregate endpoint if it becomes a real problem.
          fetchInvoices({
            ...base,
            past_due: true,
            per_page: 100,
            sort: 'invoice_date',
            order: 'asc',
          }),
          fetchDashboardStats(selectedClientId || undefined),
        ]);

        if (cancelled) return;

        // Aggregate the past-due invoices client-side.
        let pastDueTotalRsd = 0;
        let pastDueOldestDays = 0;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        for (const inv of pastDueResult.data) {
          // Prefer the NBS-converted RSD amount when available, else fall
          // back to total_amount (works for RSD-denominated invoices).
          const amount = Number(inv.total_amount_rsd ?? inv.total_amount ?? 0);
          if (Number.isFinite(amount)) pastDueTotalRsd += amount;

          const dueStr = inv.due_date ?? inv.invoice_date;
          if (dueStr) {
            const due = new Date(dueStr);
            if (!Number.isNaN(due.getTime())) {
              due.setHours(0, 0, 0, 0);
              const days = Math.floor(
                (today.getTime() - due.getTime()) / (1000 * 60 * 60 * 24),
              );
              if (days > pastDueOldestDays) pastDueOldestDays = days;
            }
          }
        }

        setData({
          totalCount: recentResult.pagination.total,
          processingCount: processingResult.pagination.total,
          reviewCount: reviewResult.pagination.total,
          verifiedCount: verifiedResult.pagination.total,
          exportedCount: exportedResult.pagination.total,
          unassignedCount: unassignedResult.pagination.total,
          pastDueCount: pastDueResult.pagination.total,
          pastDueTotalRsd,
          pastDueOldestDays,
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
