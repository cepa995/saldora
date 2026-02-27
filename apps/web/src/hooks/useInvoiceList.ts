'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchInvoices, deleteInvoice, verifyInvoice } from '@/lib/api/invoices';
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
  setSearch: (search: string) => void;
  setDateRange: (from?: string, to?: string) => void;
  setSort: (column: SortColumn) => void;
  setPage: (page: number) => void;
  toggleSelect: (id: string) => void;
  toggleSelectAll: () => void;
  clearSelection: () => void;
  batchVerify: () => Promise<void>;
  batchDelete: () => Promise<void>;
  refresh: () => void;
}

/**
 * Manages invoice list state including filters, sorting, pagination, and selection.
 */
export function useInvoiceList(): UseInvoiceListReturn {
  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0,
  });
  const [filters, setFilters] = useState<InvoiceFilters>(DEFAULT_FILTERS);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const load = useCallback(async (f: InvoiceFilters) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchInvoices(f);
      setInvoices(result.data);
      setPagination(result.pagination);
    } catch {
      setError('Greška pri učitavanju faktura');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filters);
  }, [filters, load]);

  const setStatus = useCallback((status: InvoiceStatus | undefined) => {
    setFilters((prev) => ({ ...prev, status, page: 1 }));
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
      load(filters);
    } catch {
      setError('Greška pri verifikaciji faktura');
    }
  }, [selectedIds, filters, load]);

  const batchDelete = useCallback(async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => deleteInvoice(id)));
      setSelectedIds(new Set());
      load(filters);
    } catch {
      setError('Greška pri brisanju faktura');
    }
  }, [selectedIds, filters, load]);

  const refresh = useCallback(() => {
    load(filters);
  }, [filters, load]);

  return {
    invoices,
    pagination,
    filters,
    isLoading,
    error,
    selectedIds,
    setStatus,
    setSearch,
    setDateRange,
    setSort,
    setPage,
    toggleSelect,
    toggleSelectAll,
    clearSelection,
    batchVerify,
    batchDelete,
    refresh,
  };
}
