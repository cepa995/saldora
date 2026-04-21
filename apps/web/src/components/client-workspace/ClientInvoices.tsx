'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { StatusBadge } from '@/components/StatusBadge';
import { fetchInvoices } from '@/lib/api/invoices';
import { formatAmountSr, formatDateSr } from '@/lib/formatters';
import { useOrgPath } from '@/lib/navigation';
import type { InvoiceResponse, InvoiceStatus } from '@/lib/types/invoice';

interface Props {
  clientId: string;
  period: string;
}

const STATUS_FILTERS: (InvoiceStatus | 'all')[] = [
  'all',
  'review',
  'verified',
  'exported',
  'error',
];

function periodBounds(period: string): { from: string; to: string } {
  const [y, m] = period.split('-').map(Number);
  const from = `${y}-${String(m).padStart(2, '0')}-01`;
  const lastDay = new Date(y, m, 0).getDate();
  const to = `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
  return { from, to };
}

export function ClientInvoices({ clientId, period }: Props) {
  const t = useTranslations('invoices');
  const tCommon = useTranslations('common');
  const tStatus = useTranslations('status');
  const orgPath = useOrgPath();

  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [total, setTotal] = useState(0);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { from, to } = periodBounds(period);
      const resp = await fetchInvoices({
        client_id: clientId,
        date_from: from,
        date_to: to,
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
  }, [clientId, period, statusFilter, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalAmount = useMemo(() => {
    return invoices.reduce((acc, inv) => acc + Number(inv.total_amount ?? 0), 0);
  }, [invoices]);

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {STATUS_FILTERS.map((s) => {
          const active = statusFilter === s;
          const label = s === 'all' ? tCommon('all') : tStatus(s);
          return (
            <button
              key={s}
              type="button"
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                active
                  ? 'bg-gray-900 text-white'
                  : 'bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50'
              }`}
            >
              {label}
            </button>
          );
        })}
        <span className="ml-auto text-xs text-gray-500 tabular-nums">
          {total} {t('title').toLowerCase()}
          {totalAmount > 0 && <> · {formatAmountSr(String(totalAmount), 'RSD')}</>}
        </span>
      </div>

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
              {invoices.map((inv) => (
                <tr
                  key={inv.id}
                  className="border-t border-gray-100 hover:bg-gray-50/80 transition-colors"
                >
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
