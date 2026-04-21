'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { MonthPicker } from '@/components/client-workspace/MonthPicker';
import { ClientModal } from '@/components/clients/ClientModal';
import { useAuth } from '@/contexts/AuthContext';
import { useClient } from '@/contexts/ClientContext';
import { isPlanError } from '@/lib/api-client';
import { createClient, deleteClient, fetchClient, updateClient } from '@/lib/api/clients';
import { fetchPortfolio, type PortfolioRow } from '@/lib/api/portfolio';
import type { ClientCreate, ClientResponse, ClientUpdate } from '@/lib/types/client';
import { UpgradeModal, type PlanErrorInfo } from '@/components/UpgradeModal';

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
  const diffMs = Date.now() - d.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'sada';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} d`;
  return d.toLocaleDateString(locale, { day: '2-digit', month: 'short' });
}

function severity(row: PortfolioRow): number {
  return row.blocked_count * 10 + row.pending_review_count;
}

export default function KlijentiPage({ params }: PageProps) {
  const { orgSlug } = use(params);
  const t = useTranslations('clients');
  const tPortfolio = useTranslations('portfolio');
  const tCommon = useTranslations('common');
  const { hasRole } = useAuth();
  const { refresh: refreshContext } = useClient();

  const [period, setPeriod] = useState<string>(currentYYYYMM());
  const [rows, setRows] = useState<PortfolioRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);

  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<FilterKey>('all');

  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientResponse | null>(null);
  const [loadingEditId, setLoadingEditId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PortfolioRow | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchPortfolio(period);
      setRows(resp.data);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setError(err instanceof Error ? err.message : tCommon('error'));
      }
    } finally {
      setIsLoading(false);
    }
  }, [period, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

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
    return [...out].sort((a, b) => {
      const sev = severity(b) - severity(a);
      if (sev !== 0) return sev;
      return a.name.localeCompare(b.name, 'sr-Latn');
    });
  }, [rows, search, filter]);

  async function handleEdit(clientId: string) {
    setLoadingEditId(clientId);
    try {
      const client = await fetchClient(clientId);
      setEditingClient(client);
      setModalOpen(true);
    } catch {
      setToast({ message: t('loadError'), type: 'error' });
    } finally {
      setLoadingEditId(null);
    }
  }

  async function handleSave(data: ClientCreate | ClientUpdate) {
    setSaving(true);
    try {
      if (editingClient) {
        await updateClient(editingClient.id, data as ClientUpdate);
        setToast({ message: t('editSuccess'), type: 'success' });
      } else {
        await createClient(data as ClientCreate);
        setToast({ message: t('createSuccess'), type: 'success' });
      }
      setModalOpen(false);
      setEditingClient(null);
      await load();
      refreshContext();
    } catch (err: unknown) {
      const apiErr = err as { status?: number };
      setToast({
        message: apiErr?.status === 409 ? t('duplicatePib') : t('saveError'),
        type: 'error',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(clientId: string) {
    try {
      await deleteClient(clientId);
      setToast({ message: t('deleteSuccess'), type: 'success' });
      setDeleteTarget(null);
      await load();
      refreshContext();
    } catch {
      setToast({ message: t('deleteError'), type: 'error' });
    }
  }

  if (planError) {
    return <UpgradeModal error={planError} onClose={() => window.history.back()} />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {counts.all > 0 ? (
              <>
                {counts.all} {counts.all === 1 ? t('clientSingular') : t('clientPlural')}
                {counts.needsAttention > 0 && (
                  <>
                    {' · '}
                    <span className="text-amber-700 font-medium">
                      {counts.needsAttention} {tPortfolio('filterNeedsAttention').toLowerCase()}
                    </span>
                  </>
                )}
              </>
            ) : (
              t('emptyStateSubtitle')
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <MonthPicker value={period} onChange={setPeriod} />
          {hasRole('manager') && (
            <button
              type="button"
              onClick={() => {
                setEditingClient(null);
                setModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 transition-colors shrink-0"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {t('addClient')}
            </button>
          )}
        </div>
      </header>

      {/* Filter pills — equal width */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <FilterPill
          label={tPortfolio('filterAll')}
          count={counts.all}
          active={filter === 'all'}
          tone="violet"
          onClick={() => setFilter('all')}
        />
        <FilterPill
          label={tPortfolio('filterNeedsAttention')}
          count={counts.needsAttention}
          active={filter === 'needs_attention'}
          tone="amber"
          onClick={() => setFilter('needs_attention')}
        />
        <FilterPill
          label={tPortfolio('filterOk')}
          count={counts.ok}
          active={filter === 'ok'}
          tone="emerald"
          onClick={() => setFilter('ok')}
        />
      </div>

      {/* Search — matches pill row width */}
      <div className="relative">
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

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm">
          {error}
        </div>
      )}

      {/* Grid / empty / loading */}
      {isLoading && rows.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center text-sm text-gray-500">
          {tCommon('loading')}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center">
          <p className="text-gray-600 text-base font-medium">
            {rows.length === 0 ? t('emptyState') : tCommon('noData')}
          </p>
          {rows.length === 0 && (
            <p className="text-gray-400 text-sm mt-1">{t('emptyStateSubtitle')}</p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((row) => (
            <ClientCard
              key={row.client_id}
              row={row}
              orgSlug={orgSlug}
              canEdit={hasRole('manager')}
              isEditLoading={loadingEditId === row.client_id}
              onEdit={() => handleEdit(row.client_id)}
              onDelete={() => setDeleteTarget(row)}
            />
          ))}
        </div>
      )}

      {/* Create/Edit modal */}
      {modalOpen && (
        <ClientModal
          client={editingClient}
          saving={saving}
          onSave={handleSave}
          onClose={() => {
            setModalOpen(false);
            setEditingClient(null);
          }}
        />
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('deleteConfirmTitle')}</h3>
            <p className="text-sm text-gray-600 mb-4">
              <span className="font-medium text-gray-900">{deleteTarget.name}</span>
              {' — '}
              {t('deleteConfirmMessage')}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={() => handleDelete(deleteTarget.client_id)}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                {tCommon('delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}

const TONES = {
  violet: {
    activeBg: 'bg-violet-600 text-white border-violet-600',
    inactiveCount: 'text-gray-900',
    inactiveLabel: 'text-gray-500',
  },
  amber: {
    activeBg: 'bg-amber-500 text-white border-amber-500',
    inactiveCount: 'text-gray-900',
    inactiveLabel: 'text-amber-700',
  },
  emerald: {
    activeBg: 'bg-emerald-600 text-white border-emerald-600',
    inactiveCount: 'text-gray-900',
    inactiveLabel: 'text-emerald-700',
  },
} as const;

function FilterPill({
  label,
  count,
  active,
  tone,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  tone: keyof typeof TONES;
  onClick: () => void;
}) {
  const toneCls = TONES[tone];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border px-4 py-3 text-left transition-all ${
        active
          ? toneCls.activeBg
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <p className={`text-xs ${active ? 'text-white/80' : toneCls.inactiveLabel}`}>{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${active ? 'text-white' : toneCls.inactiveCount}`}>
        {count}
      </p>
    </button>
  );
}

function ClientCard({
  row,
  orgSlug,
  canEdit,
  isEditLoading,
  onEdit,
  onDelete,
}: {
  row: PortfolioRow;
  orgSlug: string;
  canEdit: boolean;
  isEditLoading: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const t = useTranslations('clients');
  const tPortfolio = useTranslations('portfolio');
  const needsAttention = row.blocked_count > 0 || row.pending_review_count > 0;

  return (
    <div
      className={`group relative bg-white border rounded-xl flex flex-col transition-all hover:shadow-md ${
        needsAttention ? 'border-amber-200 hover:border-amber-300' : 'border-gray-200 hover:border-violet-200'
      }`}
    >
      <Link
        href={`/${orgSlug}/klijenti/${row.client_id}`}
        aria-label={`${t('openWorkspace')} — ${row.name}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
      />

      <div className="flex items-start justify-between gap-3 p-4 pb-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{row.name}</h3>
          <p className="text-xs text-gray-500 tabular-nums mt-0.5">PIB {row.pib}</p>
        </div>
        <span className="text-xs text-gray-400 tabular-nums whitespace-nowrap pt-1">
          {row.last_activity_at ? timeAgo(row.last_activity_at, 'sr-Latn') : tPortfolio('indicatorStale')}
        </span>
      </div>

      <div className="px-4 pb-3 flex-1 flex flex-wrap items-start gap-1.5">
        {row.blocked_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-rose-700 bg-rose-50 ring-1 ring-inset ring-rose-100 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            {tPortfolio('indicatorBlocked', { count: String(row.blocked_count) })}
          </span>
        )}
        {row.pending_review_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-amber-700 bg-amber-50 ring-1 ring-inset ring-amber-100 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            {tPortfolio('indicatorPending', { count: String(row.pending_review_count) })}
          </span>
        )}
        {!needsAttention && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-emerald-700 bg-emerald-50 ring-1 ring-inset ring-emerald-100 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {tPortfolio('filterOk')}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-t border-gray-100">
        <span className="text-xs text-gray-500 tabular-nums">
          {row.invoice_count} {tPortfolio('colInvoices').toLowerCase()}
        </span>
        <div className="flex items-center gap-1">
          {canEdit && (
            <div className="relative z-20 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onEdit();
                }}
                disabled={isEditLoading}
                aria-label={t('editClient')}
                className="p-1.5 text-gray-400 hover:text-violet-700 hover:bg-violet-50 rounded-md transition-colors disabled:opacity-50"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onDelete();
                }}
                aria-label={t('deleteConfirmTitle')}
                className="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M10 3h4a2 2 0 012 2v2H8V5a2 2 0 012-2z" />
                </svg>
              </button>
            </div>
          )}
          <span className="text-xs text-violet-700 font-medium pl-1">
            {tPortfolio('openWorkspace')} →
          </span>
        </div>
      </div>
    </div>
  );
}
