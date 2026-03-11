"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchSefInbox,
  processSefInvoice,
  rejectSefInvoice,
  archiveSefInvoice,
  triggerSefSync,
  fetchSefSyncStatus,
} from "@/lib/api/sef";
import { isPlanError } from "@/lib/api-client";
import type { PlanErrorInfo } from "@/components/UpgradeModal";
import type {
  SefInvoice,
  SefStatus,
  SefPaginationInfo,
  SefFilters,
  SefSortColumn,
  SortOrder,
  SefSyncStatus,
} from "@/lib/types/sef";

const DEFAULT_FILTERS: SefFilters = {
  page: 1,
  per_page: 20,
  sort: "received_at",
  order: "desc",
};

interface UseSefInboxReturn {
  invoices: SefInvoice[];
  pagination: SefPaginationInfo;
  filters: SefFilters;
  isLoading: boolean;
  error: string | null;
  planError: PlanErrorInfo | null;
  selectedIds: Set<string>;
  syncStatus: SefSyncStatus | null;
  setStatus: (status: SefStatus | undefined) => void;
  setSearch: (search: string) => void;
  setDateRange: (from?: string, to?: string) => void;
  setSort: (column: SefSortColumn) => void;
  setPage: (page: number) => void;
  toggleSelect: (id: string) => void;
  toggleSelectAll: () => void;
  clearSelection: () => void;
  batchProcess: () => Promise<void>;
  batchReject: () => Promise<void>;
  batchArchive: () => Promise<void>;
  triggerSync: () => Promise<void>;
  refresh: () => void;
}

/**
 * Manages SEF inbox state including filters, sorting, pagination, selection, and sync.
 */
export function useSefInbox(): UseSefInboxReturn {
  const [invoices, setInvoices] = useState<SefInvoice[]>([]);
  const [pagination, setPagination] = useState<SefPaginationInfo>({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0,
  });
  const [filters, setFilters] = useState<SefFilters>(DEFAULT_FILTERS);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [syncStatus, setSyncStatus] = useState<SefSyncStatus | null>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const load = useCallback(async (f: SefFilters) => {
    setIsLoading(true);
    setError(null);
    setPlanError(null);
    try {
      const result = await fetchSefInbox(f);
      setInvoices(result.data);
      setPagination(result.pagination);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setError("Greška pri učitavanju SEF faktura");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSyncStatus = useCallback(async () => {
    try {
      const status = await fetchSefSyncStatus();
      setSyncStatus(status);
    } catch {
      // Sync status is non-critical, silently ignore
    }
  }, []);

  useEffect(() => {
    load(filters);
  }, [filters, load]);

  useEffect(() => {
    loadSyncStatus();
  }, [loadSyncStatus]);

  const setStatus = useCallback((status: SefStatus | undefined) => {
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

  const setSort = useCallback((column: SefSortColumn) => {
    setFilters((prev) => {
      const order: SortOrder =
        prev.sort === column && prev.order === "asc" ? "desc" : "asc";
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

  const batchProcess = useCallback(async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => processSefInvoice(id)));
      setSelectedIds(new Set());
      load(filters);
      loadSyncStatus();
    } catch (err) {
      if (isPlanError(err)) setPlanError(err.planError as PlanErrorInfo);
      else setError("Greška pri obradi SEF faktura");
    }
  }, [selectedIds, filters, load, loadSyncStatus]);

  const batchReject = useCallback(async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => rejectSefInvoice(id)));
      setSelectedIds(new Set());
      load(filters);
    } catch (err) {
      if (isPlanError(err)) setPlanError(err.planError as PlanErrorInfo);
      else setError("Greška pri odbijanju SEF faktura");
    }
  }, [selectedIds, filters, load]);

  const batchArchive = useCallback(async () => {
    const ids = Array.from(selectedIds);
    try {
      await Promise.all(ids.map((id) => archiveSefInvoice(id)));
      setSelectedIds(new Set());
      load(filters);
    } catch (err) {
      if (isPlanError(err)) setPlanError(err.planError as PlanErrorInfo);
      else setError("Greška pri arhiviranju SEF faktura");
    }
  }, [selectedIds, filters, load]);

  const doTriggerSync = useCallback(async () => {
    try {
      const status = await triggerSefSync();
      setSyncStatus(status);
      load(filters);
    } catch (err) {
      if (isPlanError(err)) setPlanError(err.planError as PlanErrorInfo);
      else setError("Greška pri sinhronizaciji sa SEF sistemom");
    }
  }, [filters, load]);

  const refresh = useCallback(() => {
    load(filters);
    loadSyncStatus();
  }, [filters, load, loadSyncStatus]);

  return {
    invoices,
    pagination,
    filters,
    isLoading,
    error,
    planError,
    selectedIds,
    syncStatus,
    setStatus,
    setSearch,
    setDateRange,
    setSort,
    setPage,
    toggleSelect,
    toggleSelectAll,
    clearSelection,
    batchProcess,
    batchReject,
    batchArchive,
    triggerSync: doTriggerSync,
    refresh,
  };
}
