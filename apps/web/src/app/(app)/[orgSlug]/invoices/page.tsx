'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useOrgPath } from '@/lib/navigation';
import { useInvoiceList } from '@/hooks/useInvoiceList';
import { StatusBadge } from '@/components/StatusBadge';
import { ConfidenceBadge } from '@/components/ConfidenceBadge';
import { ExportDialog } from '@/components/ExportDialog';
import { fetchQueueInfo } from '@/lib/api/invoices';
import { formatDateSr, formatAmountSr } from '@/lib/formatters';
import type { InvoiceStatus, SortColumn } from '@/lib/types/invoice';

const STATUS_OPTIONS: (InvoiceStatus | undefined)[] = [
  undefined,
  'processing',
  'review',
  'verified',
  'exported',
  'error',
];

const SORTABLE_COLUMNS: { key: SortColumn; labelKey: string }[] = [
  { key: 'status', labelKey: 'columnStatus' },
  { key: 'invoice_date', labelKey: 'columnDate' },
  { key: 'total_amount', labelKey: 'columnTotal' },
  { key: 'confidence_score', labelKey: 'columnConfidence' },
];

export default function InvoicesPage() {
  const router = useRouter();
  const { hasRole } = useAuth();
  const orgPath = useOrgPath();
  const t = useTranslations('invoices');
  const tCommon = useTranslations('common');
  const tStatus = useTranslations('status');
  const tDetail = useTranslations('detail');
  const canWrite = hasRole('operator');
  const canDelete = hasRole('manager');
  // Default this surface to the "inbox" view — invoices not yet attached to
  // a client. User can switch to "Sve fakture" via the segmented toggle.
  // Passing the initial filter to the hook makes the *first* fetch use the
  // right scope; setting it via useEffect later caused a flash of the wrong
  // count on the "Nesortirano" pill while the out-of-scope request was in flight.
  const {
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
    toggleSelect,
    toggleSelectAll,
    clearSelection,
    batchVerify,
    batchDelete,
    refresh,
  } = useInvoiceList({ unassigned: true });

  const [searchValue, setSearchValue] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const hasProcessing = invoices.some(inv => inv.status === 'processing');
  const [rawQueueInfo, setRawQueueInfo] = useState<{ queue_depth: number; your_pending: number; estimated_minutes: number } | null>(null);

  // Derive displayed queue info — only show when processing
  const queueInfo = hasProcessing ? rawQueueInfo : null;

  // Poll queue info when there are processing invoices
  useEffect(() => {
    if (!hasProcessing) return;

    let active = true;
    async function checkQueue() {
      try {
        const info = await fetchQueueInfo();
        if (active) setRawQueueInfo(info.your_pending > 0 ? info : null);
      } catch {
        if (active) setRawQueueInfo(null);
      }
    }

    checkQueue();
    const interval = setInterval(checkQueue, 10000);
    return () => { active = false; clearInterval(interval); };
  }, [hasProcessing]);

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

  function handleBatchDelete() {
    setShowDeleteConfirm(true);
  }

  async function confirmBatchDelete() {
    await batchDelete();
    setShowDeleteConfirm(false);
  }

  function getSortIcon(column: SortColumn) {
    if (filters.sort !== column) return null;
    return filters.order === 'asc' ? (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  }

  const totalPages = pagination.total_pages;
  const currentPage = pagination.page;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-gray-900">
            {filters.unassigned ? 'Prijemno sanduče' : t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {filters.unassigned
              ? 'Fakture koje još nisu dodeljene klijentu. Dodelite ih da se pojave u radnom prostoru.'
              : 'Sve fakture u organizaciji, kroz sve klijente.'}
          </p>
        </div>
        {canWrite && (
          <Link
            href={orgPath("/upload")}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm shadow-violet-200"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {t('uploadInvoice')}
          </Link>
        )}
      </div>

      {/* Scope toggle — Prijemno sanduče vs. Sve fakture */}
      <div className="inline-flex items-center gap-1 p-1 bg-gray-100 rounded-xl">
        <button
          type="button"
          onClick={() => setUnassigned(true)}
          className={`px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            filters.unassigned
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Nesortirano
          {filters.unassigned && pagination.total > 0 && (
            <span className="ml-1.5 tabular-nums text-xs text-gray-500">
              ({pagination.total})
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setUnassigned(false)}
          className={`px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            !filters.unassigned
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Sve fakture
        </button>
      </div>

      {/* Queue info banner */}
      {queueInfo && queueInfo.your_pending > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 bg-violet-50 border border-violet-200 rounded-xl">
          <div className="animate-spin w-4 h-4 border-2 border-violet-300 border-t-violet-600 rounded-full shrink-0" />
          <div className="text-sm text-violet-700">
            <span className="font-medium">
              {queueInfo.your_pending} {queueInfo.your_pending === 1 ? t('invoiceInQueue') : t('invoicesInQueue')}
            </span>
            {' · '}
            {t('estimatedWait', { minutes: String(queueInfo.estimated_minutes) })}
            {queueInfo.queue_depth > queueInfo.your_pending && (
              <span className="text-violet-500">
                {' · '}{t('totalInQueue', { count: String(queueInfo.queue_depth) })}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Search + Filters */}
      <div className="space-y-4">
        {/* Search input */}
        <div className="relative">
          <svg
            className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchValue}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder={t('searchPlaceholder')}
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow"
          />
        </div>

        {/* Filter chips + date range — single wrapping row */}
        <div className="flex flex-wrap items-center gap-2">
          {STATUS_OPTIONS.map((status) => {
            const isActive = filters.status === status;
            const label = status ? tStatus(status) : tCommon('all');
            return (
              <button
                key={status ?? 'all'}
                onClick={() => setStatus(status)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-violet-50 text-violet-700 ring-1 ring-violet-600/20'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {label}
              </button>
            );
          })}

          {/* Separator dot on larger screens */}
          <span className="hidden sm:block w-1 h-1 rounded-full bg-gray-300" />

          {/* Accounting review filter */}
          <button
            onClick={() => setAccountingReview(filters.accounting_review === true ? undefined : true)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all inline-flex items-center gap-1.5 ${
              filters.accounting_review === true
                ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t('needsAccountingReview')}
          </button>

          {/* PDV book type filters */}
          <button
            onClick={() => setBookType(filters.book_type === 'KPR' ? undefined : 'KPR')}
            title={tDetail('bookTypeKPR')}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              filters.book_type === 'KPR'
                ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            KPR
          </button>
          <button
            onClick={() => setBookType(filters.book_type === 'KIR' ? undefined : 'KIR')}
            title={tDetail('bookTypeKIR')}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              filters.book_type === 'KIR'
                ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            KIR
          </button>

          {/* Date range — inline with the chips, pushed to the right on wide screens */}
          <div className="flex items-center gap-2 sm:ml-auto">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => handleDateFrom(e.target.value)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              title={t('dateFrom')}
              aria-label={t('dateFrom')}
            />
            <span className="text-gray-500 text-xs" aria-hidden="true">—</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => handleDateTo(e.target.value)}
              className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              title={t('dateTo')}
              aria-label={t('dateTo')}
            />
          </div>
        </div>
      </div>

      {/* Batch action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 bg-violet-50 rounded-xl border border-violet-100">
          <span className="text-sm font-medium text-violet-700">
            {tCommon('selected', { count: selectedIds.size.toString() })}
          </span>
          <div className="flex items-center gap-2 ml-auto">
            {canWrite && (
              <button
                onClick={batchVerify}
                className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors"
              >
                {t('batchVerify')}
              </button>
            )}
            <button
              onClick={() => setShowExportDialog(true)}
              className="px-3 py-1.5 bg-violet-600 text-white text-xs font-medium rounded-lg hover:bg-violet-700 transition-colors"
            >
              {t('batchExport')}
            </button>
            {canDelete && (
              <button
                onClick={handleBatchDelete}
                className="px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 transition-colors"
              >
                {t('batchDelete')}
              </button>
            )}
            <button
              onClick={clearSelection}
              className="px-3 py-1.5 text-gray-600 text-xs font-medium hover:text-gray-900 transition-colors"
            >
              {tCommon('cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-50 rounded-xl border border-red-100">
          <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-red-700">{error}</span>
          <button
            onClick={refresh}
            className="ml-auto text-sm font-medium text-red-700 hover:text-red-800"
          >
            {tCommon('retry')}
          </button>
        </div>
      )}

      {/* Table / Content */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <SkeletonTable />
        ) : invoices.length === 0 ? (
          <EmptyState
            hasFilters={!!(filters.status || filters.search || filters.date_from || filters.date_to)}
            canUpload={canWrite}
            uploadHref={orgPath("/upload")}
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
                        checked={selectedIds.size === invoices.length && invoices.length > 0}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                        aria-label={t('selectAll')}
                      />
                    </th>
                    {SORTABLE_COLUMNS.map((col) => (
                      <th
                        key={col.key}
                        scope="col"
                        className="px-4 py-3 text-left"
                        aria-sort={
                          filters.sort === col.key
                            ? filters.order === 'asc'
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                        }
                      >
                        <button
                          onClick={() => setSort(col.key)}
                          className={`inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wider transition-colors ${
                            filters.sort === col.key
                              ? 'text-violet-700'
                              : 'text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          {t(col.labelKey)}
                          {getSortIcon(col.key)}
                        </button>
                      </th>
                    ))}
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('columnInvoiceNumber')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('columnSeller')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('columnBuyer')}
                    </th>
                    <th scope="col" className="w-20 px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => (
                    <tr
                      key={invoice.id}
                      onClick={() => router.push(orgPath(`/invoices/${invoice.id}`))}
                      className="border-b border-gray-50 hover:bg-violet-50/30 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(invoice.id)}
                          onChange={() => toggleSelect(invoice.id)}
                          className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                        />
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-1.5">
                          <StatusBadge status={invoice.status} />
                          {invoice.pdv_book_type && (
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold leading-none ${
                                invoice.pdv_book_type === 'KPR'
                                  ? 'bg-blue-50 text-blue-700'
                                  : 'bg-emerald-50 text-emerald-700'
                              }`}
                            >
                              {invoice.pdv_book_type}
                            </span>
                          )}
                          {invoice.accounting_review_needed && (
                            <svg className="w-4 h-4 text-amber-500 shrink-0" fill="currentColor" viewBox="0 0 20 20" role="img" aria-label={t('needsAccountingReview')}>
                              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-sm text-gray-700">
                        {formatDateSr(invoice.invoice_date)}
                      </td>
                      <td className="px-4 py-3.5 text-sm font-medium text-gray-900">
                        {formatAmountSr(invoice.total_amount, invoice.currency)}
                      </td>
                      <td className="px-4 py-3.5">
                        <ConfidenceBadge confidence={invoice.confidence_score} />
                      </td>
                      <td className="px-4 py-3.5 text-sm text-gray-700 font-mono">
                        {invoice.invoice_number || (
                          <span className="text-gray-500 font-sans">{t('noInvoiceNumber')}</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-sm text-gray-700 truncate max-w-[200px]">
                        {invoice.seller?.name || (
                          <span className="text-gray-500">{t('noSeller')}</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-sm text-gray-700 truncate max-w-[200px]">
                        {invoice.buyer?.name || (
                          <span className="text-gray-500">{t('noBuyer')}</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                        <Link
                          href={orgPath(`/invoices/${invoice.id}`)}
                          className="text-xs font-medium text-violet-600 hover:text-violet-700 transition-colors"
                        >
                          {t('view')}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden divide-y divide-gray-200">
              {invoices.map((invoice) => (
                <Link
                  key={invoice.id}
                  href={orgPath(`/invoices/${invoice.id}`)}
                  className="flex items-start gap-3 px-4 py-4 hover:bg-gray-50 active:bg-gray-100 transition-colors"
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
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <StatusBadge status={invoice.status} />
                        {invoice.pdv_book_type && (
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold leading-none ${
                              invoice.pdv_book_type === 'KPR'
                                ? 'bg-blue-50 text-blue-700'
                                : 'bg-emerald-50 text-emerald-700'
                            }`}
                          >
                            {invoice.pdv_book_type}
                          </span>
                        )}
                        {invoice.accounting_review_needed && (
                          <svg className="w-4 h-4 text-amber-500 shrink-0" fill="currentColor" viewBox="0 0 20 20" role="img" aria-label={t('needsAccountingReview')}>
                            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <span className="text-[15px] font-semibold text-gray-900 tabular-nums">
                        {formatAmountSr(invoice.total_amount, invoice.currency)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 truncate">
                      {invoice.seller?.name || t('noSeller')}
                    </p>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500 font-mono">
                          {invoice.invoice_number || t('noInvoiceNumber')}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatDateSr(invoice.invoice_date)}
                        </span>
                      </div>
                      <ConfidenceBadge confidence={invoice.confidence_score} />
                    </div>
                  </div>
                  <svg className="w-4 h-4 text-gray-400 shrink-0 mt-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-sm text-gray-500">
            {tCommon('showingRange', {
              from: String((currentPage - 1) * pagination.per_page + 1),
              to: String(Math.min(currentPage * pagination.per_page, pagination.total)),
              total: String(pagination.total),
            })}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage <= 1}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label={tCommon('previous')}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            {getPageNumbers(currentPage, totalPages).map((p, i) =>
              p === '...' ? (
                <span key={`ellipsis-${i}`} className="px-2 py-1 text-sm text-gray-400">
                  ...
                </span>
              ) : (
                <button
                  key={p}
                  onClick={() => setPage(p as number)}
                  className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
                    currentPage === p
                      ? 'bg-violet-600 text-white shadow-sm'
                      : 'text-gray-700 hover:bg-gray-100'
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
              aria-label={tCommon('next')}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowDeleteConfirm(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('deleteConfirmTitle')}</h3>
            <p className="text-sm text-gray-600 mb-6">
              {t('deleteConfirmBatch', { count: selectedIds.size.toString() })}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={confirmBatchDelete}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                {tCommon('delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export dialog */}
      {showExportDialog && (
        <ExportDialog
          invoiceIds={Array.from(selectedIds)}
          onClose={() => setShowExportDialog(false)}
          onSuccess={() => {
            clearSelection();
            refresh();
          }}
        />
      )}
    </div>
  );
}

/**
 * Generate page number array with ellipsis for pagination.
 */
function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages: (number | '...')[] = [1];
  if (current > 3) pages.push('...');
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i);
  }
  if (current < total - 2) pages.push('...');
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
          <div className="w-28 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-16 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="flex-1 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-32 h-4 bg-gray-100 rounded animate-pulse" />
          <div className="w-32 h-4 bg-gray-100 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({ hasFilters, canUpload = true, uploadHref }: { hasFilters: boolean; canUpload?: boolean; uploadHref: string }) {
  const t = useTranslations('invoices');

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-16 h-16 bg-violet-50 rounded-2xl flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-1">
        {hasFilters ? t('noResults') : t('emptyState')}
      </h3>
      <p className="text-sm text-gray-500 mb-6 text-center max-w-sm">
        {hasFilters ? t('noResultsSubtitle') : t('emptyStateSubtitle')}
      </p>
      {!hasFilters && canUpload && (
        <Link
          href={uploadHref}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          {t('uploadInvoice')}
        </Link>
      )}
    </div>
  );
}
