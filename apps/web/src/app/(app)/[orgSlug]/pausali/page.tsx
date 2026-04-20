'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchPortfolio } from '@/lib/api/pausal';
import type { AlertLevel, PortfolioRow } from '@/lib/types/pausal';

import { AlertBadge } from '@/components/pausal/AlertBadge';

interface PageProps {
  params: Promise<{ orgSlug: string }>;
}

type SortKey = 'name' | 'revenue' | 'pct';

const ALERT_ORDER: Record<AlertLevel, number> = {
  ok: 0,
  warning: 1,
  critical: 2,
  exceeded: 3,
};

function fmtRsd(amount: string | number): string {
  const n = typeof amount === 'string' ? Number(amount) : amount;
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('sr-Latn-RS', {
    maximumFractionDigits: 0,
  }).format(Math.round(n));
}

function MiniBar({ pct, level }: { pct: number; level: AlertLevel }) {
  const clamped = Math.min(pct, 100);
  const fill =
    level === 'ok'
      ? 'bg-emerald-500'
      : level === 'warning'
        ? 'bg-amber-500'
        : level === 'critical'
          ? 'bg-orange-500'
          : 'bg-rose-500';
  const track =
    level === 'ok'
      ? 'bg-emerald-100'
      : level === 'warning'
        ? 'bg-amber-100'
        : level === 'critical'
          ? 'bg-orange-100'
          : 'bg-rose-100';
  return (
    <div className="flex items-center gap-2">
      <div className={`relative h-1.5 w-20 sm:w-24 rounded-full overflow-hidden ${track}`}>
        <div
          className={`absolute inset-y-0 left-0 ${fill} transition-all duration-500 ease-out rounded-full`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-gray-600 font-medium w-12 text-right">
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

export default function PausalPortfolioPage({ params }: PageProps) {
  const { orgSlug } = use(params);
  const t = useTranslations('pausal');
  const tCommon = useTranslations('common');

  const currentYear = useMemo(() => new Date().getFullYear(), []);
  const [year, setYear] = useState<number>(currentYear);
  const [rows, setRows] = useState<PortfolioRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [alertFilter, setAlertFilter] = useState<AlertLevel | 'all'>('all');
  const [sortKey, setSortKey] = useState<SortKey>('pct');
  const [sortDesc, setSortDesc] = useState(true);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchPortfolio(year);
      setRows(resp.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [year, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let out = rows.filter((r) => {
      if (alertFilter !== 'all' && r.overall_alert_level !== alertFilter) return false;
      if (!q) return true;
      return (
        r.name.toLowerCase().includes(q) ||
        r.pib.toLowerCase().includes(q) ||
        (r.activity_code ?? '').toLowerCase().includes(q)
      );
    });
    const direction = sortDesc ? -1 : 1;
    out = [...out].sort((a, b) => {
      if (sortKey === 'name') {
        return a.name.localeCompare(b.name, 'sr-Latn') * direction * -1;
      }
      if (sortKey === 'revenue') {
        return (Number(a.total_revenue) - Number(b.total_revenue)) * direction;
      }
      if (sortKey === 'pct') {
        const deltaPct = a.pausal_status_pct - b.pausal_status_pct;
        if (deltaPct !== 0) return deltaPct * direction;
        return (
          (ALERT_ORDER[a.overall_alert_level] - ALERT_ORDER[b.overall_alert_level]) *
          direction
        );
      }
      return 0;
    });
    return out;
  }, [rows, search, alertFilter, sortKey, sortDesc]);

  const totalsByLevel = useMemo(() => {
    const counts: Record<AlertLevel, number> = {
      ok: 0,
      warning: 0,
      critical: 0,
      exceeded: 0,
    };
    for (const r of rows) counts[r.overall_alert_level] += 1;
    return counts;
  }, [rows]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDesc((v) => !v);
    } else {
      setSortKey(key);
      setSortDesc(key !== 'name');
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
            {t('portfolioTitle')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('portfolioSubtitle')}</p>
        </div>
        <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setYear(year - 1)}
            className="p-2 rounded-md hover:bg-white text-gray-600 transition-colors"
            aria-label={tCommon('previous')}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="px-3 text-sm font-semibold text-gray-900 tabular-nums">
            {year}
          </span>
          <button
            type="button"
            onClick={() => setYear(year + 1)}
            disabled={year >= currentYear}
            className="p-2 rounded-md hover:bg-white text-gray-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label={tCommon('next')}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </header>

      {/* Summary tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(['ok', 'warning', 'critical', 'exceeded'] as AlertLevel[]).map((level) => (
          <button
            type="button"
            key={level}
            onClick={() =>
              setAlertFilter((prev) => (prev === level ? 'all' : level))
            }
            className={`rounded-2xl bg-white border px-4 py-3 text-left transition-all ${
              alertFilter === level
                ? 'border-violet-400 ring-2 ring-violet-100 shadow-sm'
                : 'border-gray-100 hover:border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <AlertBadge level={level} />
              <span className="text-2xl font-bold tabular-nums text-gray-900">
                {totalsByLevel[level]}
              </span>
            </div>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10a7.5 7.5 0 0013.15 6.65z" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('filterSearchPlaceholder')}
            className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
          />
        </div>
        <select
          value={alertFilter}
          onChange={(e) => setAlertFilter(e.target.value as AlertLevel | 'all')}
          className="px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
        >
          <option value="all">{t('filterAllLevels')}</option>
          <option value="ok">{t('alertOk')}</option>
          <option value="warning">{t('alertWarning')}</option>
          <option value="critical">{t('alertCritical')}</option>
          <option value="exceeded">{t('alertExceeded')}</option>
        </select>
      </div>

      {/* Table */}
      <section className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
        {error ? (
          <div className="p-6 text-sm text-rose-700 bg-rose-50 border-b border-rose-200">
            {error}
          </div>
        ) : null}

        {isLoading && rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-gray-500">
            {tCommon('loading')}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-gray-500">
            {t('portfolioEmpty')}
          </div>
        ) : (
          <>
            {/* Mobile: cards */}
            <ul className="sm:hidden divide-y divide-gray-100">
              {filtered.map((r) => (
                <li key={r.client_id}>
                  <Link
                    href={`/${orgSlug}/clients/${r.client_id}/pausal`}
                    className="block p-4 active:bg-gray-50"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-gray-900 truncate">{r.name}</h3>
                        <p className="text-xs text-gray-500 mt-0.5">
                          PIB {r.pib}
                          {r.activity_code && (
                            <>
                              <span className="mx-1.5 text-gray-300">·</span>
                              {r.activity_code}
                            </>
                          )}
                        </p>
                      </div>
                      <AlertBadge level={r.overall_alert_level} />
                    </div>
                    <div className="flex items-end justify-between mt-3">
                      <span className="text-lg font-bold tabular-nums text-gray-900">
                        {fmtRsd(r.total_revenue)}{' '}
                        <span className="text-xs font-normal text-gray-400">RSD</span>
                      </span>
                      <MiniBar
                        pct={r.pausal_status_pct}
                        level={r.overall_alert_level}
                      />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>

            {/* Desktop: table */}
            <div className="hidden sm:block overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-100">
                    <th className="text-left px-5 sm:px-6 py-3 font-medium">
                      <button
                        type="button"
                        onClick={() => toggleSort('name')}
                        className="inline-flex items-center gap-1 hover:text-gray-900"
                      >
                        {t('colName')}
                        {sortKey === 'name' && (
                          <span className="text-gray-400">{sortDesc ? '↓' : '↑'}</span>
                        )}
                      </button>
                    </th>
                    <th className="text-left px-4 py-3 font-medium">{t('colPib')}</th>
                    <th className="text-left px-4 py-3 font-medium">{t('colActivity')}</th>
                    <th className="text-right px-4 py-3 font-medium">
                      <button
                        type="button"
                        onClick={() => toggleSort('revenue')}
                        className="inline-flex items-center gap-1 hover:text-gray-900"
                      >
                        {t('colYTDRevenue')}
                        {sortKey === 'revenue' && (
                          <span className="text-gray-400">{sortDesc ? '↓' : '↑'}</span>
                        )}
                      </button>
                    </th>
                    <th className="text-left px-4 py-3 font-medium">
                      <button
                        type="button"
                        onClick={() => toggleSort('pct')}
                        className="inline-flex items-center gap-1 hover:text-gray-900"
                      >
                        {t('colPausalPct')}
                        {sortKey === 'pct' && (
                          <span className="text-gray-400">{sortDesc ? '↓' : '↑'}</span>
                        )}
                      </button>
                    </th>
                    <th className="text-right px-5 sm:px-6 py-3 font-medium">
                      {t('colAlert')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.map((r) => (
                    <tr
                      key={r.client_id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => {
                        window.location.href = `/${orgSlug}/clients/${r.client_id}/pausal`;
                      }}
                    >
                      <td className="px-5 sm:px-6 py-3 font-medium text-gray-900">
                        {r.name}
                      </td>
                      <td className="px-4 py-3 text-gray-600 tabular-nums">{r.pib}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {r.activity_code ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums font-medium text-gray-900">
                        {fmtRsd(r.total_revenue)}{' '}
                        <span className="text-xs text-gray-400">RSD</span>
                      </td>
                      <td className="px-4 py-3">
                        <MiniBar
                          pct={r.pausal_status_pct}
                          level={r.overall_alert_level}
                        />
                      </td>
                      <td className="px-5 sm:px-6 py-3 text-right">
                        <AlertBadge level={r.overall_alert_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
