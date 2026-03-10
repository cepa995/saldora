"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { useOrgPath } from "@/lib/navigation";
import { useSefInbox } from "@/hooks/useSefInbox";
import {
  formatDateSr,
  formatAmountSr,
  formatRelativeTime,
} from "@/lib/formatters";
import type { SefStatus, SefSortColumn } from "@/lib/types/sef";

const SEF_STATUS_CONFIG: Record<
  SefStatus,
  { dotClass: string; badgeClass: string; labelKey: string }
> = {
  new: {
    dotClass: "bg-blue-500",
    badgeClass: "bg-blue-50 text-blue-700 ring-1 ring-blue-600/20",
    labelKey: "statusNew",
  },
  pending: {
    dotClass: "bg-amber-500",
    badgeClass: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
    labelKey: "statusPending",
  },
  processed: {
    dotClass: "bg-green-500",
    badgeClass: "bg-green-50 text-green-700 ring-1 ring-green-600/20",
    labelKey: "statusProcessed",
  },
  rejected: {
    dotClass: "bg-red-500",
    badgeClass: "bg-red-50 text-red-700 ring-1 ring-red-600/20",
    labelKey: "statusRejected",
  },
  archived: {
    dotClass: "bg-gray-400",
    badgeClass: "bg-gray-50 text-gray-600 ring-1 ring-gray-500/20",
    labelKey: "statusArchived",
  },
};

const STATUS_OPTIONS: (SefStatus | undefined)[] = [
  undefined,
  "new",
  "pending",
  "processed",
  "rejected",
  "archived",
];

const SORTABLE_COLUMNS: { key: SefSortColumn; labelKey: string }[] = [
  { key: "status", labelKey: "columnStatus" },
  { key: "received_at", labelKey: "columnDate" },
  { key: "invoice_date", labelKey: "columnInvoiceDate" },
  { key: "amount", labelKey: "columnAmount" },
];

export default function SefInboxPage() {
  const router = useRouter();
  const { hasRole } = useAuth();
  const orgPath = useOrgPath();
  const t = useTranslations("sef");
  const tCommon = useTranslations("common");
  const canWrite = hasRole("operator");
  const {
    invoices,
    pagination,
    filters,
    isLoading,
    error,
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
    triggerSync,
    refresh,
  } = useSefInbox();

  const [searchValue, setSearchValue] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);

  function handleSearch(value: string) {
    setSearchValue(value);
    setSearch(value);
  }

  function handleDateFrom(value: string) {
    setDateFrom(value);
    setDateRange(value || undefined, dateTo || undefined);
  }

  function handleDateTo(value: string) {
    setDateTo(value);
    setDateRange(dateFrom || undefined, value || undefined);
  }

  async function handleSync() {
    setIsSyncing(true);
    try {
      await triggerSync();
    } finally {
      setIsSyncing(false);
    }
  }

  function getSortIcon(column: SefSortColumn) {
    if (filters.sort !== column) return null;
    return filters.order === "asc" ? (
      <svg
        className="w-3.5 h-3.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 15l7-7 7 7"
        />
      </svg>
    ) : (
      <svg
        className="w-3.5 h-3.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 9l-7 7-7-7"
        />
      </svg>
    );
  }

  const totalPages = pagination.total_pages;
  const currentPage = pagination.page;

  return (
    <div className="space-y-6">
      {/* Page header with sync status */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <div className="flex items-center justify-center sm:justify-start gap-3 mt-1">
            <span className="text-sm text-gray-500">
              {syncStatus?.last_sync_at
                ? t("lastSync", {
                    time: formatRelativeTime(syncStatus.last_sync_at),
                  })
                : t("neverSynced")}
            </span>
            {syncStatus && syncStatus.pending_count > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 ring-1 ring-blue-600/20">
                {t("pendingCount", { count: String(syncStatus.pending_count) })}
              </span>
            )}
          </div>
        </div>
        {canWrite && (
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm shadow-violet-200 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <svg
              className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {isSyncing ? t("syncing") : t("syncNow")}
          </button>
        )}
      </div>

      {/* Search + Filters */}
      <div className="space-y-4">
        <div className="relative">
          <svg
            className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={searchValue}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
          />
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((status) => {
              const isActive = filters.status === status;
              const label = status
                ? t(SEF_STATUS_CONFIG[status].labelKey)
                : tCommon("all");
              return (
                <button
                  key={status ?? "all"}
                  onClick={() => setStatus(status)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    isActive
                      ? "bg-violet-50 text-violet-700 ring-1 ring-violet-600/20"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-center gap-2 sm:ml-auto">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => handleDateFrom(e.target.value)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              title={t("dateFrom")}
              aria-label={t("dateFrom")}
            />
            <span className="text-gray-500 text-xs" aria-hidden="true">
              —
            </span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => handleDateTo(e.target.value)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              title={t("dateTo")}
              aria-label={t("dateTo")}
            />
          </div>
        </div>
      </div>

      {/* Batch action bar */}
      {canWrite && selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 bg-violet-50 rounded-xl border border-violet-100">
          <span className="text-sm font-medium text-violet-700">
            {tCommon("selected", { count: selectedIds.size.toString() })}
          </span>
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={batchProcess}
              className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors"
            >
              {t("batchProcess")}
            </button>
            <button
              onClick={batchReject}
              className="px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 transition-colors"
            >
              {t("batchReject")}
            </button>
            <button
              onClick={batchArchive}
              className="px-3 py-1.5 bg-gray-600 text-white text-xs font-medium rounded-lg hover:bg-gray-700 transition-colors"
            >
              {t("batchArchive")}
            </button>
            <button
              onClick={clearSelection}
              className="px-3 py-1.5 text-gray-600 text-xs font-medium hover:text-gray-900 transition-colors"
            >
              {tCommon("cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-50 rounded-xl border border-red-100">
          <svg
            className="w-5 h-5 text-red-500 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-sm text-red-700">{error}</span>
          <button
            onClick={refresh}
            className="ml-auto text-sm font-medium text-red-700 hover:text-red-800"
          >
            {tCommon("retry")}
          </button>
        </div>
      )}

      {/* Table / Content */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <SkeletonTable />
        ) : invoices.length === 0 ? (
          <EmptyState
            hasFilters={
              !!(
                filters.status ||
                filters.search ||
                filters.date_from ||
                filters.date_to
              )
            }
          />
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50/50 border-b border-gray-100">
                    <th scope="col" className="w-12 px-4 py-3">
                      <input
                        type="checkbox"
                        checked={
                          selectedIds.size === invoices.length &&
                          invoices.length > 0
                        }
                        onChange={toggleSelectAll}
                        className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                        aria-label={t("selectAll")}
                      />
                    </th>
                    {SORTABLE_COLUMNS.map((col) => (
                      <th
                        key={col.key}
                        scope="col"
                        className="px-4 py-3 text-left"
                        aria-sort={
                          filters.sort === col.key
                            ? filters.order === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                      >
                        <button
                          onClick={() => setSort(col.key)}
                          className={`inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wider transition-colors ${
                            filters.sort === col.key
                              ? "text-violet-700"
                              : "text-gray-500 hover:text-gray-700"
                          }`}
                        >
                          {t(col.labelKey)}
                          {getSortIcon(col.key)}
                        </button>
                      </th>
                    ))}
                    <th
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {t("columnInvoiceNumber")}
                    </th>
                    <th
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {t("columnSupplier")}
                    </th>
                    <th scope="col" className="w-20 px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => {
                    const statusConfig = SEF_STATUS_CONFIG[invoice.status];
                    return (
                      <tr
                        key={invoice.id}
                        onClick={() => router.push(orgPath(`/sef-inbox/${invoice.id}`))}
                        className="border-b border-gray-50 hover:bg-violet-50/30 transition-colors cursor-pointer"
                      >
                        <td
                          className="px-4 py-3.5"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={selectedIds.has(invoice.id)}
                            onChange={() => toggleSelect(invoice.id)}
                            className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                          />
                        </td>
                        <td className="px-4 py-3.5">
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusConfig.badgeClass}`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${statusConfig.dotClass}`}
                            />
                            {t(statusConfig.labelKey)}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-sm text-gray-700">
                          {formatDateSr(invoice.received_at)}
                        </td>
                        <td className="px-4 py-3.5 text-sm text-gray-700">
                          {formatDateSr(invoice.invoice_date)}
                        </td>
                        <td className="px-4 py-3.5 text-sm font-medium text-gray-900">
                          {formatAmountSr(invoice.amount, invoice.currency)}
                        </td>
                        <td className="px-4 py-3.5 text-sm text-gray-700 font-mono">
                          {invoice.invoice_number || (
                            <span className="text-gray-500 font-sans">
                              {t("noInvoiceNumber")}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-sm text-gray-700 truncate max-w-[200px]">
                          {invoice.supplier_name || (
                            <span className="text-gray-500">
                              {t("noSupplier")}
                            </span>
                          )}
                        </td>
                        <td
                          className="px-4 py-3.5 text-right"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Link
                            href={orgPath(`/sef-inbox/${invoice.id}`)}
                            className="text-xs font-medium text-violet-600 hover:text-violet-700 transition-colors"
                          >
                            {t("view")}
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden divide-y divide-gray-100">
              {invoices.map((invoice) => {
                const statusConfig = SEF_STATUS_CONFIG[invoice.status];
                return (
                  <Link
                    key={invoice.id}
                    href={orgPath(`/sef-inbox/${invoice.id}`)}
                    className="flex items-start gap-3 px-4 py-4 hover:bg-gray-50 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(invoice.id)}
                      onChange={(e) => {
                        e.preventDefault();
                        toggleSelect(invoice.id);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="mt-1 w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500 shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusConfig.badgeClass}`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${statusConfig.dotClass}`}
                          />
                          {t(statusConfig.labelKey)}
                        </span>
                        <span className="text-sm font-semibold text-gray-900">
                          {formatAmountSr(invoice.amount, invoice.currency)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 truncate">
                        {invoice.supplier_name || t("noSupplier")}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-gray-500 font-mono">
                          {invoice.invoice_number || t("noInvoiceNumber")}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatDateSr(invoice.received_at)}
                        </span>
                      </div>
                    </div>
                    <svg
                      className="w-4 h-4 text-gray-400 shrink-0 mt-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </Link>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-sm text-gray-500">
            {tCommon("showingRange", {
              from: String((currentPage - 1) * pagination.per_page + 1),
              to: String(
                Math.min(currentPage * pagination.per_page, pagination.total),
              ),
              total: String(pagination.total),
            })}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage <= 1}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label={tCommon("previous")}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            {getPageNumbers(currentPage, totalPages).map((p, i) =>
              p === "..." ? (
                <span
                  key={`ellipsis-${i}`}
                  className="px-2 py-1 text-sm text-gray-400"
                >
                  ...
                </span>
              ) : (
                <button
                  key={p}
                  onClick={() => setPage(p as number)}
                  className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                    currentPage === p
                      ? "bg-violet-600 text-white shadow-sm"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  {p}
                </button>
              ),
            )}
            <button
              onClick={() => setPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label={tCommon("next")}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages: (number | "...")[] = [1];
  if (current > 3) pages.push("...");
  for (
    let i = Math.max(2, current - 1);
    i <= Math.min(total - 1, current + 1);
    i++
  ) {
    pages.push(i);
  }
  if (current < total - 2) pages.push("...");
  pages.push(total);
  return pages;
}

function SkeletonTable() {
  return (
    <div className="p-4 space-y-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <div className="w-4 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-20 h-6 bg-gray-100 rounded-full animate-pulse" />
          <div className="w-24 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-24 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-28 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="flex-1 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-32 h-4 bg-gray-100 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  const t = useTranslations("sef");

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-16 h-16 bg-violet-50 rounded-2xl flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-violet-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-1">
        {hasFilters ? t("noResults") : t("emptyState")}
      </h3>
      <p className="text-sm text-gray-500 mb-6 text-center max-w-sm">
        {hasFilters ? t("noResultsSubtitle") : t("emptyStateSubtitle")}
      </p>
    </div>
  );
}
