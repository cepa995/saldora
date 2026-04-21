'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { MonthPicker } from '@/components/client-workspace/MonthPicker';
import { fetchPortfolio, type PortfolioRow } from '@/lib/api/portfolio';

interface PageProps {
  params: Promise<{ orgSlug: string }>;
}

type FilterKey = 'all' | 'needs_attention' | 'ok';

function currentYYYYMM(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function timeAgo(iso: string | null, locale: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  const now = Date.now();
  const diffMs = now - d.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} d`;
  return d.toLocaleDateString(locale, { day: '2-digit', month: 'short' });
}

function severity(row: PortfolioRow): number {
  // Higher = more attention needed
  return row.blocked_count * 10 + row.pending_review_count;
}

export default function PortfolioPage({ params }: PageProps) {
  const { orgSlug } = use(params);
  const t = useTranslations('portfolio');
  const tCommon = useTranslations('common');

  const [period, setPeriod] = useState<string>(currentYYYYMM());
  const [rows, setRows] = useState<PortfolioRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<FilterKey>('all');

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchPortfolio(period);
      setRows(resp.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [period, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => {
    let needsAttention = 0;
    let ok = 0;
    for (const r of rows) {
      if (r.blocked_count > 0 || r.pending_review_count > 0) needsAttention += 1;
      else ok += 1;
    }
    return { all: rows.length, needsAttention, ok };
  }, [rows]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let out = rows;
    if (filter === 'needs_attention') {
      out = out.filter((r) => r.blocked_count > 0 || r.pending_review_count > 0);
    } else if (filter === 'ok') {
      out = out.filter((r) => r.blocked_count === 0 && r.pending_review_count === 0);
    }
    if (q) {
      out = out.filter((r) => r.name.toLowerCase().includes(q) || r.pib.includes(q));
    }
    // Severity desc, then name asc
    return [...out].sort((a, b) => {
      const sev = severity(b) - severity(a);
      if (sev !== 0) return sev;
      return a.name.localeCompare(b.name, 'sr-Latn');
    });
  }, [rows, search, filter]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <MonthPicker value={period} onChange={setPeriod} />
      </header>

      {/* Summary pills */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <button
          type="button"
          onClick={() => setFilter('all')}
          className={`rounded-xl border px-4 py-3 text-left transition-all ${
            filter === 'all'
              ? 'border-violet-400 ring-2 ring-violet-100 bg-white'
              : 'border-gray-100 bg-white hover:border-gray-200'
          }`}
        >
          <p className="text-xs text-gray-500">{t('filterAll')}</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums">{counts.all}</p>
        </button>
        <button
          type="button"
          onClick={() => setFilter('needs_attention')}
          className={`rounded-xl border px-4 py-3 text-left transition-all ${
            filter === 'needs_attention'
              ? 'border-amber-400 ring-2 ring-amber-100 bg-white'
              : 'border-gray-100 bg-white hover:border-gray-200'
          }`}
        >
          <p className="text-xs text-amber-700">{t('filterNeedsAttention')}</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums">{counts.needsAttention}</p>
        </button>
        <button
          type="button"
          onClick={() => setFilter('ok')}
          className={`rounded-xl border px-4 py-3 text-left transition-all ${
            filter === 'ok'
              ? 'border-emerald-400 ring-2 ring-emerald-100 bg-white'
              : 'border-gray-100 bg-white hover:border-gray-200'
          }`}
        >
          <p className="text-xs text-emerald-700">{t('filterOk')}</p>
          <p className="text-2xl font-bold text-gray-900 tabular-nums">{counts.ok}</p>
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10a7.5 7.5 0 0013.15 6.65z" />
        </svg>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('searchPlaceholder')}
          className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
        />
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm">
          {error}
        </div>
      )}

      {/* Grid */}
      {isLoading && rows.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center text-sm text-gray-500">
          {tCommon('loading')}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center text-sm text-gray-500">
          {rows.length === 0 ? t('empty') : tCommon('noData')}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((row) => (
            <PortfolioCard key={row.client_id} row={row} orgSlug={orgSlug} />
          ))}
        </div>
      )}
    </div>
  );
}

function PortfolioCard({ row, orgSlug }: { row: PortfolioRow; orgSlug: string }) {
  const t = useTranslations('portfolio');
  const needsAttention = row.blocked_count > 0 || row.pending_review_count > 0;

  return (
    <Link
      href={`/${orgSlug}/klijenti/${row.client_id}`}
      className={`rounded-2xl border bg-white p-4 transition-all hover:shadow-md hover:border-gray-200 ${
        needsAttention ? 'border-amber-200' : 'border-gray-100'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{row.name}</h3>
          <p className="text-xs text-gray-500 tabular-nums mt-0.5">PIB {row.pib}</p>
        </div>
        <span className="text-xs text-gray-400 tabular-nums whitespace-nowrap">
          {row.last_activity_at ? timeAgo(row.last_activity_at, 'sr-Latn') : t('indicatorStale')}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {row.blocked_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-rose-700 bg-rose-50 ring-1 ring-inset ring-rose-100 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            {t('indicatorBlocked', { count: String(row.blocked_count) })}
          </span>
        )}
        {row.pending_review_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-amber-700 bg-amber-50 ring-1 ring-inset ring-amber-100 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            {t('indicatorPending', { count: String(row.pending_review_count) })}
          </span>
        )}
        {!needsAttention && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-emerald-700 bg-emerald-50 ring-1 ring-inset ring-emerald-100 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {t('filterOk')}
          </span>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
        <span className="tabular-nums">
          {row.invoice_count} {t('colInvoices').toLowerCase()}
        </span>
        <span className="text-violet-700 font-medium">
          {t('openWorkspace')} →
        </span>
      </div>
    </Link>
  );
}
