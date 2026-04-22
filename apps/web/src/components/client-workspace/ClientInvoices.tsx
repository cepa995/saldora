'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { StatusBadge } from '@/components/StatusBadge';
import { FilterPill, type PillTone } from '@/components/clients/FilterPill';
import { deleteInvoice, fetchInvoices, verifyInvoice } from '@/lib/api/invoices';
import { formatAmountSr, formatDateSr } from '@/lib/formatters';
import { useOrgPath } from '@/lib/navigation';
import type { InvoiceResponse, InvoiceStatus } from '@/lib/types/invoice';

interface Props {
  clientId: string;
}

const STATUS_FILTERS: (InvoiceStatus | 'all')[] = [
  'all',
  'review',
  'verified',
  'exported',
  'error',
];

const STATUS_TONE: Record<InvoiceStatus | 'all', PillTone> = {
  all: 'neutral',
  processing: 'amber',
  review: 'blue',
  verified: 'emerald',
  exported: 'violet',
  error: 'rose',
};

export function ClientInvoices({ clientId }: Props) {
  const t = useTranslations('invoices');
  const tCommon = useTranslations('common');
  const tStatus = useTranslations('status');
  const orgPath = useOrgPath();

  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [total, setTotal] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkWorking, setIsBulkWorking] = useState(false);
  const [showBulkDelete, setShowBulkDelete] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchInvoices({
        client_id: clientId,
        status: statusFilter === 'all' ? undefined : statusFilter,
        sort: 'invoice_date',
        order: 'desc',
        per_page: 100,
      });
      setInvoices(resp.data);
      setTotal(resp.pagination.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, statusFilter, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  // Drop selection whenever the filter changes — stale IDs confuse the user.
  useEffect(() => {
    setSelectedIds(new Set());
  }, [statusFilter]);

  const totalAmount = useMemo(() => {
    return invoices.reduce((acc, inv) => acc + Number(inv.total_amount ?? 0), 0);
  }, [invoices]);

  const allSelected = invoices.length > 0 && selectedIds.size === invoices.length;
  const someSelected = selectedIds.size > 0 && !allSelected;

  function toggleOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (allSelected) setSelectedIds(new Set());
    else setSelectedIds(new Set(invoices.map((i) => i.id)));
  }

  async function runBulkVerify() {
    const ids = Array.from(selectedIds);
    setIsBulkWorking(true);
    try {
      await Promise.all(ids.map((id) => verifyInvoice(id)));
      setSelectedIds(new Set());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsBulkWorking(false);
    }
  }

  async function runBulkDelete() {
    const ids = Array.from(selectedIds);
    setIsBulkWorking(true);
    setShowBulkDelete(false);
    try {
      await Promise.all(ids.map((id) => deleteInvoice(id)));
      setSelectedIds(new Set());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsBulkWorking(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-2 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <FilterPill
            key={s}
            label={s === 'all' ? tCommon('all') : tStatus(s)}
            active={statusFilter === s}
            tone={STATUS_TONE[s]}
            onClick={() => setStatusFilter(s)}
          />
        ))}
        <span className="ml-auto text-xs text-stone-500 tabular-nums">
          {total} {t('title').toLowerCase()}
          {totalAmount > 0 && <> · {formatAmountSr(String(totalAmount), 'RSD')}</>}
        </span>
      </div>

      {/* Bulk action bar — only visible when 1+ selected */}
      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-stone-900 text-white">
          <span className="text-sm font-medium tabular-nums">
            {selectedIds.size} {tCommon('selected', { count: String(selectedIds.size) })}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={runBulkVerify}
              disabled={isBulkWorking}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.25} d="M5 13l4 4L19 7" />
              </svg>
              {t('batchVerify')}
            </button>
            <button
              type="button"
              onClick={() => setShowBulkDelete(true)}
              disabled={isBulkWorking}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-rose-500 text-white rounded-lg hover:bg-rose-600 transition-colors disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22" />
              </svg>
              {t('batchDelete')}
            </button>
            <button
              type="button"
              onClick={() => setSelectedIds(new Set())}
              disabled={isBulkWorking}
              className="px-3 py-1.5 text-xs font-medium text-white/80 hover:text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {tCommon('cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm">
          {error}
        </div>
      )}

      {/* Empty / loading / table */}
      {isLoading && invoices.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center text-sm text-gray-500">
          {tCommon('loading')}
        </div>
      ) : invoices.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-white/60 p-10 text-center">
          <p className="text-sm text-gray-500">{t('emptyState')}</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50/60">
              <tr>
                <th className="w-10 px-3 py-2.5">
                  <input
                    type="checkbox"
                    aria-label={t('selectAll')}
                    checked={allSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelected;
                    }}
                    onChange={toggleAll}
                    className="w-4 h-4 rounded border-stone-300 text-violet-600 focus:ring-violet-500 cursor-pointer"
                  />
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  {t('columnDate')}
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  {t('columnInvoiceNumber')}
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  {t('columnSeller')}
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  {t('columnStatus')}
                </th>
                <th className="px-4 py-2.5 text-right text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  {t('columnTotal')}
                </th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => {
                const isSelected = selectedIds.has(inv.id);
                return (
                  <tr
                    key={inv.id}
                    className={`border-t border-gray-100 transition-colors ${
                      isSelected ? 'bg-violet-50/40 hover:bg-violet-50/60' : 'hover:bg-gray-50/80'
                    }`}
                  >
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleOne(inv.id)}
                        aria-label={`Odaberi fakturu ${inv.invoice_number ?? inv.id}`}
                        className="w-4 h-4 rounded border-stone-300 text-violet-600 focus:ring-violet-500 cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-600 tabular-nums whitespace-nowrap">
                      {formatDateSr(inv.invoice_date)}
                    </td>
                    <td className="px-4 py-3 text-gray-900 font-medium">
                      <Link
                        href={orgPath(`/invoices/${inv.id}`)}
                        className="hover:text-violet-700"
                      >
                        {inv.invoice_number || '—'}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600 truncate max-w-[260px]">
                      {inv.seller?.name || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900 tabular-nums whitespace-nowrap">
                      {inv.total_amount
                        ? formatAmountSr(inv.total_amount, inv.currency)
                        : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Bulk-delete confirmation */}
      {showBulkDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full">
            <h3 className="text-lg font-semibold text-stone-900 mb-2">
              {t('batchDelete')}
            </h3>
            <p className="text-sm text-stone-600 mb-5">
              {t('deleteConfirmBatch', { count: String(selectedIds.size) })}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowBulkDelete(false)}
                className="px-4 py-2 text-sm text-stone-600 hover:bg-stone-100 rounded-lg"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={runBulkDelete}
                className="px-4 py-2 text-sm bg-rose-600 text-white rounded-lg hover:bg-rose-700"
              >
                {tCommon('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
