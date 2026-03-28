'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { fetchDpu, type DpuItem, type DpuResponse } from '@/lib/api/reports';

// ── Helpers ──────────────────────────────────────────────────────────

function todayIso(): string {
  return new Date().toISOString().split('T')[0];
}

function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('sr-Latn-RS', { maximumFractionDigits: 3 }).format(n);
}

function fmtPrice(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('sr-Latn-RS', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

// ── Row state (closing stock editable) ───────────────────────────────

interface RowState extends DpuItem {
  closingInput: string;
}

function computeRow(item: DpuItem, closingInput: string): {
  closing: number | null;
  consumed: number | null;
  revenue: number | null;
} {
  const closingRaw = closingInput.trim();
  const closing = closingRaw !== '' ? parseFloat(closingRaw) : null;
  const consumed = closing !== null ? item.opening_stock + item.purchased - closing : null;
  const revenue = consumed !== null && item.selling_price !== null
    ? consumed * item.selling_price
    : null;
  return { closing, consumed, revenue };
}

// ── XLSX export ──────────────────────────────────────────────────────

async function exportXlsx(date: string, rows: RowState[], t: ReturnType<typeof useTranslations>) {
  // Build CSV as a simple fallback (no xlsx dependency required)
  const headers = [
    'R.br',
    t('itemName'),
    t('unit'),
    t('openingStock'),
    t('purchased'),
    t('closingStock'),
    t('consumed'),
    t('sellingPrice'),
    t('revenue'),
  ];

  const dataRows = rows.map((row, i) => {
    const { closing, consumed, revenue } = computeRow(row, row.closingInput);
    return [
      i + 1,
      row.description,
      row.unit_of_measure ?? '',
      row.opening_stock,
      row.purchased,
      closing ?? '',
      consumed ?? '',
      row.selling_price ?? '',
      revenue !== null ? revenue.toFixed(2) : '',
    ];
  });

  const csvContent = [headers, ...dataRows]
    .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n');

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dpu-${date}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Main page ────────────────────────────────────────────────────────

export default function DpuPage() {
  const t = useTranslations('dpu');
  const tc = useTranslations('common');

  const [date, setDate] = useState(todayIso());
  const [data, setData] = useState<DpuResponse | null>(null);
  const [rows, setRows] = useState<RowState[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDpu(date);
      setData(res);
      setRows(
        res.items.map((item) => ({
          ...item,
          closingInput: item.closing_stock !== null ? String(item.closing_stock) : '',
        })),
      );
    } catch {
      setError(tc('error'));
      setData(null);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [date, tc]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function updateClosing(index: number, value: string) {
    setRows((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], closingInput: value };
      return next;
    });
  }

  // Compute totals from current row states
  const totalRevenue = rows.reduce((sum, row) => {
    const { revenue } = computeRow(row, row.closingInput);
    return sum + (revenue ?? 0);
  }, 0);

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => exportXlsx(date, rows, t)}
          disabled={rows.length === 0}
          className="flex items-center gap-2 px-4 py-2 text-sm text-violet-700 border border-violet-200 font-medium rounded-lg hover:bg-violet-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {t('exportXlsx')}
        </button>
      </div>

      {/* Date picker */}
      <div className="flex items-center gap-3 mb-5">
        <label className="text-sm font-medium text-gray-700">{t('date')}:</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
        />
      </div>

      {/* Summary cards */}
      {data && !loading && (
        <div className="grid grid-cols-2 gap-4 mb-5">
          <div className="bg-white border border-gray-200 rounded-2xl px-5 py-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{t('totalPurchased')}</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{fmtPrice(data.total_purchased_value)} RSD</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-2xl px-5 py-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{t('totalRevenue')}</p>
            <p className="text-xl font-bold text-violet-700 tabular-nums">
              {rows.some((r) => r.closingInput !== '') ? `${fmtPrice(totalRevenue)} RSD` : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        {error ? (
          <div className="px-6 py-12 text-center">
            <p className="text-sm text-red-600">{error}</p>
            <button onClick={loadData} className="mt-3 text-sm text-violet-600 hover:underline">
              {tc('retry')}
            </button>
          </div>
        ) : loading ? (
          <div className="animate-pulse">
            <div className="h-10 bg-gray-50 border-b border-gray-100" />
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex gap-4 px-4 py-3 border-b border-gray-100 last:border-0">
                <div className="h-4 bg-gray-200 rounded w-8" />
                <div className="h-4 bg-gray-200 rounded flex-1" />
                <div className="h-4 bg-gray-200 rounded w-12" />
                <div className="h-4 bg-gray-200 rounded w-16" />
                <div className="h-4 bg-gray-200 rounded w-16" />
                <div className="h-8 bg-gray-200 rounded w-24" />
                <div className="h-4 bg-gray-200 rounded w-16" />
                <div className="h-4 bg-gray-200 rounded w-20" />
                <div className="h-4 bg-gray-200 rounded w-20" />
              </div>
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <p className="text-sm text-gray-500">{t('noData')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-10">R.br</th>
                  <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('itemName')}</th>
                  <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">{t('unit')}</th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-28">{t('openingStock')}</th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-24">{t('purchased')}</th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-32">{t('closingStock')}</th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-24">{t('consumed')}</th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-28">{t('sellingPrice')}</th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-28">{t('revenue')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((row, i) => {
                  const { consumed, revenue } = computeRow(row, row.closingInput);
                  return (
                    <tr key={i} className={`${i % 2 === 1 ? 'bg-gray-50/40' : ''} hover:bg-violet-50/20 transition-colors`}>
                      <td className="px-3 py-2.5 text-gray-400 tabular-nums">{i + 1}</td>
                      <td className="px-3 py-2.5 font-medium text-gray-900 max-w-[220px] truncate">
                        {row.description}
                      </td>
                      <td className="px-3 py-2.5 text-center text-gray-500">{row.unit_of_measure ?? '—'}</td>
                      <td className="px-3 py-2.5 text-right text-gray-600 tabular-nums">{fmtNum(row.opening_stock)}</td>
                      <td className="px-3 py-2.5 text-right text-gray-900 tabular-nums font-medium">{fmtNum(row.purchased)}</td>
                      <td className="px-3 py-2.5 text-right">
                        <input
                          type="number"
                          step="0.001"
                          min="0"
                          value={row.closingInput}
                          onChange={(e) => updateClosing(i, e.target.value)}
                          placeholder="0"
                          className="w-24 px-2 py-1 text-right text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 tabular-nums"
                        />
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums">
                        {consumed !== null ? (
                          <span className={`font-medium ${consumed < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                            {fmtNum(consumed)}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right text-gray-600 tabular-nums">{fmtPrice(row.selling_price)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums">
                        {revenue !== null ? (
                          <span className="font-medium text-violet-700">{fmtPrice(revenue)}</span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {rows.length > 0 && (
                <tfoot>
                  <tr className="bg-gray-50 border-t-2 border-gray-200 font-semibold">
                    <td colSpan={4} className="px-3 py-3 text-xs text-gray-500 uppercase tracking-wider">
                      Ukupno
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums text-gray-900">
                      {fmtNum(rows.reduce((s, r) => s + r.purchased, 0))}
                    </td>
                    <td />
                    <td className="px-3 py-3 text-right tabular-nums text-gray-900">
                      {rows.every((r) => r.closingInput !== '')
                        ? fmtNum(rows.reduce((s, r) => {
                            const { consumed } = computeRow(r, r.closingInput);
                            return s + (consumed ?? 0);
                          }, 0))
                        : '—'}
                    </td>
                    <td />
                    <td className="px-3 py-3 text-right tabular-nums text-violet-700">
                      {rows.some((r) => r.closingInput !== '') ? fmtPrice(totalRevenue) : '—'}
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
