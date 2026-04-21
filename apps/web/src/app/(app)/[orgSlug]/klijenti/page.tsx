'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { ClientAvatar } from '@/components/clients/ClientAvatar';
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

function formatCompactNumber(n: number): string {
  return n.toLocaleString('sr-Latn');
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'sada';
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d`;
  return d.toLocaleDateString('sr-Latn', { day: '2-digit', month: 'short' });
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

  const [period] = useState<string>(currentYYYYMM());
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
    let pending = 0;
    let blocked = 0;
    let totalInvoices = 0;
    for (const r of rows) {
      totalInvoices += r.invoice_count;
      pending += r.pending_review_count;
      blocked += r.blocked_count;
      if (r.blocked_count > 0 || r.pending_review_count > 0) needsAttention += 1;
      else ok += 1;
    }
    return { all: rows.length, needsAttention, ok, pending, blocked, totalInvoices };
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
    <div className="mx-auto w-full max-w-[110rem] space-y-7">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-[32px] sm:text-[36px] font-bold text-stone-900 tracking-tight leading-[1.1]">
            {t('title')}
          </h1>
          <p className="text-sm text-stone-500 mt-2">
            {counts.all > 0 ? (
              <>
                <span className="tabular-nums">{counts.all}</span>{' '}
                {counts.all === 1 ? t('clientSingular') : t('clientPlural')}
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
        {hasRole('manager') && (
          <button
            type="button"
            onClick={() => {
              setEditingClient(null);
              setModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 transition-colors shrink-0 shadow-sm shadow-violet-600/10"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.25} d="M12 4v16m8-8H4" />
            </svg>
            {t('addClient')}
          </button>
        )}
      </header>

      {/* Agency summary strip */}
      {counts.all > 0 && (
        <AgencySummary
          clients={counts.all}
          invoices={counts.totalInvoices}
          pending={counts.pending}
          blocked={counts.blocked}
        />
      )}

      {/* Sticky filter + search bar */}
      <div className="sticky top-0 z-20 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-3 bg-gradient-to-b from-gray-50 via-gray-50/95 to-gray-50/70 backdrop-blur-sm">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex items-center gap-1.5 flex-wrap">
            <FilterPill
              label={tPortfolio('filterAll')}
              count={counts.all}
              active={filter === 'all'}
              tone="neutral"
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
          <div className="relative flex-1 sm:max-w-md sm:ml-auto">
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10a7.5 7.5 0 0013.15 6.65z" />
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('searchPlaceholder')}
              className="w-full pl-10 pr-3 py-2 text-sm bg-white border border-stone-200 rounded-lg focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500 placeholder:text-stone-400"
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm">
          {error}
        </div>
      )}

      {/* Grid / empty / loading */}
      {isLoading && rows.length === 0 ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-500">
          {tCommon('loading')}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          total={rows.length}
          filter={filter}
          emptyLabel={t('emptyState')}
          emptySubtitle={t('emptyStateSubtitle')}
          noDataLabel={tCommon('noData')}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4">
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

      {/* Modals */}
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
      {deleteTarget && (
        <DeleteDialog
          clientName={deleteTarget.name}
          title={t('deleteConfirmTitle')}
          message={t('deleteConfirmMessage')}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => handleDelete(deleteTarget.client_id)}
          cancelLabel={tCommon('cancel')}
          confirmLabel={tCommon('delete')}
        />
      )}
      {toast && (
        <div
          className={`fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}

function AgencySummary({
  clients,
  invoices,
  pending,
  blocked,
}: {
  clients: number;
  invoices: number;
  pending: number;
  blocked: number;
}) {
  const t = useTranslations('clients');
  const tPortfolio = useTranslations('portfolio');
  const tWorkspace = useTranslations('clientWorkspace');

  const stats: { label: string; value: number; tone: 'neutral' | 'amber' | 'rose' }[] = [
    { label: t('title'), value: clients, tone: 'neutral' },
    { label: tPortfolio('colInvoices'), value: invoices, tone: 'neutral' },
    { label: tWorkspace('tilePending'), value: pending, tone: pending > 0 ? 'amber' : 'neutral' },
    { label: tWorkspace('tileBlocked'), value: blocked, tone: blocked > 0 ? 'rose' : 'neutral' },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-stone-200/70 rounded-2xl bg-white ring-1 ring-stone-200/70 overflow-hidden">
      {stats.map((s) => (
        <div key={s.label} className="px-5 py-4 min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
            {s.label}
          </p>
          <p
            className={`mt-1 text-[28px] font-bold tabular-nums leading-none ${
              s.tone === 'amber'
                ? 'text-amber-700'
                : s.tone === 'rose'
                  ? 'text-rose-700'
                  : 'text-stone-900'
            }`}
          >
            {formatCompactNumber(s.value)}
          </p>
        </div>
      ))}
    </div>
  );
}

const PILL_TONES = {
  neutral: {
    active: 'bg-violet-600 text-white',
    inactive: 'text-stone-600 bg-stone-100 hover:bg-stone-200',
  },
  amber: {
    active: 'bg-amber-100 text-amber-800 ring-1 ring-amber-200',
    inactive: 'text-stone-600 bg-stone-100 hover:bg-stone-200',
  },
  emerald: {
    active: 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200',
    inactive: 'text-stone-600 bg-stone-100 hover:bg-stone-200',
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
  tone: keyof typeof PILL_TONES;
  onClick: () => void;
}) {
  const cls = PILL_TONES[tone];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full transition-all ${
        active ? cls.active : cls.inactive
      }`}
    >
      {label}
      <span
        className={`tabular-nums px-1.5 py-0.5 text-[10px] rounded-full ${
          active ? 'bg-white/20' : 'bg-white text-stone-500'
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function EmptyState({
  total,
  filter,
  emptyLabel,
  emptySubtitle,
  noDataLabel,
}: {
  total: number;
  filter: FilterKey;
  emptyLabel: string;
  emptySubtitle: string;
  noDataLabel: string;
}) {
  if (total === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-stone-200 bg-white p-12 text-center">
        <div className="w-12 h-12 mx-auto rounded-xl bg-stone-100 flex items-center justify-center mb-4">
          <svg className="w-6 h-6 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87M9 12a4 4 0 100-8 4 4 0 000 8zm6-4a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        </div>
        <p className="text-base font-semibold text-stone-900">{emptyLabel}</p>
        <p className="text-sm text-stone-500 mt-1">{emptySubtitle}</p>
      </div>
    );
  }
  // We have clients, but the filter is empty — positive signal on "OK" filter
  if (filter === 'needs_attention') {
    return (
      <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-10 text-center">
        <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-100 flex items-center justify-center mb-4">
          <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-base font-semibold text-emerald-900">Sve je u redu</p>
        <p className="text-sm text-emerald-700/80 mt-1">Nijedan klijent ne zahteva pažnju za ovaj mesec.</p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-500">
      {noDataLabel}
    </div>
  );
}

function DeleteDialog({
  clientName,
  title,
  message,
  onCancel,
  onConfirm,
  cancelLabel,
  confirmLabel,
}: {
  clientName: string;
  title: string;
  message: string;
  onCancel: () => void;
  onConfirm: () => void;
  cancelLabel: string;
  confirmLabel: string;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full">
        <h3 className="text-lg font-semibold text-stone-900 mb-2">{title}</h3>
        <p className="text-sm text-stone-600 mb-5">
          <span className="font-medium text-stone-900">{clientName}</span> — {message}
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-stone-600 hover:bg-stone-100 rounded-lg"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm bg-rose-600 text-white rounded-lg hover:bg-rose-700"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
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

  const severity = row.blocked_count > 0 ? 'blocked' : row.pending_review_count > 0 ? 'pending' : 'ok';
  const toneCls =
    severity === 'blocked'
      ? 'bg-rose-50/50 ring-1 ring-rose-200 hover:ring-rose-300'
      : severity === 'pending'
        ? 'bg-amber-50/40 ring-1 ring-amber-200 hover:ring-amber-300'
        : 'bg-white ring-1 ring-stone-200/80 hover:ring-stone-300';

  return (
    <div
      className={`group relative rounded-2xl flex flex-col overflow-hidden transition-all hover:-translate-y-px hover:shadow-lg shadow-[0_1px_2px_rgba(0,0,0,0.02)] ${toneCls}`}
    >
      <Link
        href={`/${orgSlug}/klijenti/${row.client_id}`}
        aria-label={`${t('openWorkspace')} — ${row.name}`}
        className="absolute inset-0 z-10 rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
      />

      <div className="flex items-start gap-3 p-4">
        <ClientAvatar name={row.name} seed={row.client_id} size="md" />
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-stone-900 truncate leading-tight">{row.name}</h3>
          <p className="text-[11px] text-stone-500 tabular-nums mt-0.5 tracking-wide">PIB {row.pib}</p>
        </div>
        <span className="text-[11px] text-stone-400 tabular-nums whitespace-nowrap pt-1">
          {row.last_activity_at ? timeAgo(row.last_activity_at) : tPortfolio('indicatorStale')}
        </span>
      </div>

      <div className="px-4 pb-3 flex-1">
        <div className="flex items-center gap-3 text-xs text-stone-500">
          <span className="tabular-nums">
            <span className="font-semibold text-stone-700">{row.invoice_count}</span>{' '}
            {tPortfolio('colInvoices').toLowerCase()}
          </span>
          {severity === 'blocked' && (
            <span className="inline-flex items-center gap-1 text-rose-700 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
              {tPortfolio('indicatorBlocked', { count: String(row.blocked_count) })}
            </span>
          )}
          {severity === 'pending' && (
            <span className="inline-flex items-center gap-1 text-amber-700 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              {tPortfolio('indicatorPending', { count: String(row.pending_review_count) })}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 px-4 py-3 border-t border-stone-200/60 bg-white/40">
        <span className="text-xs text-violet-700 font-medium">
          {tPortfolio('openWorkspace')} →
        </span>
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
              className="p-1.5 text-stone-400 hover:text-violet-700 hover:bg-violet-50 rounded-md transition-colors disabled:opacity-50"
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
              className="p-1.5 text-stone-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M10 3h4a2 2 0 012 2v2H8V5a2 2 0 012-2z" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
