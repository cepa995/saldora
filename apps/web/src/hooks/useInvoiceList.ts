'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchInvoices, deleteInvoice, verifyInvoice } from '@/lib/api/invoices';
import { useClient } from '@/contexts/ClientContext';
import type {
  InvoiceResponse,
  InvoiceStatus,
  PaginationInfo,
  InvoiceFilters,
  SortColumn,
  SortOrder,
} from '@/lib/types/invoice';

const DEFAULT_FILTERS: InvoiceFilters = {
  page: 1,
  per_page: 20,
  sort: 'created_at',
  order: 'desc',
};

interface UseInvoiceListReturn {
  invoices: InvoiceResponse[];
  pagination: PaginationInfo;
  filters: InvoiceFilters;
  isLoading: boolean;
  error: string | null;
  selectedIds: Set<string>;
  setStatus: (status: InvoiceStatus | undefined) => void;
  setAccountingReview: (value: boolean | undefined) => void;
  setBookType: (value: 'KPR' | 'KIR' | undefined) => void;
  setSearch: (search: string) => void;
  setDateRange: (from?: string, to?: string) => void;
  setSort: (column: SortColumn) => void;
  setPage: (page: number) => void;
  setUnassigned: (value: boolean) => void;
  setPastDue: (value: boolean) => void;
  toggleSelect: (id: string) => void;
  toggleSelectAll: () => void;
  clearSelection: () => void;
  batchVerify: () => Promise<void>;
  batchDelete: () => Promise<void>;
  refresh: () => void;
}

/**
 * Manages invoice list state including filters, sorting, pagination, and selection.
 *
 * Accepts an optional initial-filter override so the first fetch on mount
 * runs with the intended scope — avoids a flash of stale counts that
 * happens if callers try to call setXyz() from a useEffect after mount.
 */
export function useInvoiceList(
  initial: Partial<InvoiceFilters> = {},
): UseInvoiceListReturn {
  const { selectedClientId } = useClient();
  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0,
  });
  const [filters, setFilters] = useState<InvoiceFilters>({
    ...DEFAULT_FILTERS,
    ...initial,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const load = useCallback(async (f: InvoiceFilters, clientId?: string | null) => {
    setIsLoading(true);
    setError(null);
    try {
      const filtersWithClient = clientId ? { ...f, client_id: clientId } : f;
      const result = await fetchInvoices(filtersWithClient);
      setInvoices(result.data);
      setPagination(result.pagination);
    } catch {
      setError('Greška pri učitavanju faktura');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filters, selectedClientId);
  }, [filters, selectedClientId, load]);

  // Auto-refresh every 8s when there are invoices still processing.
  // Uses a ref to avoid restarting the interval on every render.
  const hasProcessingRef = useRef(false);
  hasProcessingRef.current = invoices.some((inv) => inv.status === 'processing');

  useEffect(() => {
    const interval = setInterval(() => {
      if (hasProcessingRef.current) {
        load(filters, selectedClientId);
      }
    }, 8000);
    return () => clearInterval(interval);
  }, [invoices, filters, selectedClientId, load]);

  const setStatus = useCallback((status: InvoiceStatus | undefined) => {
    setFilters((prev) => ({ ...prev, status, page: 1 }));
    setSelectedIds(new Set());
  }, []);

  const setAccountingReview = useCallback((value: boolean | undefined) => {
    setFilters((prev) => ({ ...prev, accounting_review: value, page: 1 }));
    setSelectedIds(new Set());
  }, []);

  const setBookType = useCallback((value: 'KPR' | 'KIR' | undefined) => {
    setFilters((prev) => ({ ...prev, book_type: value, page: 1 }));
    setSelectedIds(new Set());
  }, []);

  const setSearch = useCallback((search: string) => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: search || undefined, page: 1 }));
      setSelectedIds(new Set());
    }, 300);
  }, []);

  const setDateRange = useCallback((from?: string, to?: string) => {
    setFilters((prev) => ({
      ...prev,
      date_from: from || undefined,
      date_to: to || undefined,
      page: 1,
    }));
  }, []);

  const setSort = useCallback((column: SortColumn) => {
    setFilters((prev) => {
      const order: SortOrder =
        prev.sort === column && prev.order === 'asc' ? 'desc' : 'asc';
      return { ...prev, sort: column, order, page: 1 };
    });
  }, []);

  const setPage = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }));
    setSelectedIds(new Set());
  }, []);

  const setUnassigned = useCallback((value: boolean) => {
    setFilters((prev) => ({
      ...prev,
      unassigned: value ? true : undefined,
      page: 1,
    }));
    setSelectedIds(new Set());
  }, []);

  const setPastDue = useCallback((value: boolean) => {
    setFilters((prev) => ({
      ...prev,
      past_due: value ? true : undefined,
      page: 1,
    }));
    setSelectedIds(new Set());
  }, []);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === invoices.length) return new Set();
      return new Set(invoices.map((inv) => inv.id));
    });
  }, [invoices]);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const batchVerify = useCallback(async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => verifyInvoice(id)));
      setSelectedIds(new Set());
      load(filters, selectedClientId);
    } catch (err: unknown) {
      const apiErr = err as { message?: string; status?: number };
      if (apiErr?.status === 400 && apiErr.message?.includes("'verified'")) {
        setError('Odabrane fakture su već verifikovane');
      } else if (apiErr?.status === 400 && apiErr.message?.includes('status')) {
        setError('Odabrane fakture nisu u statusu za verifikaciju');
      } else {
        setError(apiErr?.message || 'Greška pri verifikaciji faktura');
      }
    }
  }, [selectedIds, filters, selectedClientId, load]);

  const batchDelete = useCallback(async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => deleteInvoice(id)));
      setSelectedIds(new Set());
      load(filters, selectedClientId);
    } catch {
      setError('Greška pri brisanju faktura');
    }
  }, [selectedIds, filters, selectedClientId, load]);

  const refresh = useCallback(() => {
    load(filters, selectedClientId);
  }, [filters, selectedClientId, load]);

  return {
    invoices,
    pagination,
    filters,
    isLoading,
    error,
    selectedIds,
    setStatus,
    setAccountingReview,
    setBookType,
    setSearch,
    setDateRange,
    setSort,
    setPage,
    setUnassigned,
    setPastDue,
    toggleSelect,
    toggleSelectAll,
    clearSelection,
    batchVerify,
    batchDelete,
    refresh,
  };
}
