'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { use, useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { ClientAvatar } from '@/components/clients/ClientAvatar';
import { ClientModal } from '@/components/clients/ClientModal';
import { ClientInvoices } from '@/components/client-workspace/ClientInvoices';
import { ClientRules } from '@/components/client-workspace/ClientRules';
import { ClientTimeline } from '@/components/client-workspace/ClientTimeline';
import { TabBar, type TabKey } from '@/components/client-workspace/TabBar';
import { ReportsSurface } from '@/components/reports/ReportsSurface';
import { useAuth } from '@/contexts/AuthContext';
import {
  fetchClient,
  fetchClientWorkspaceStats,
  toggleClientActive,
  updateClient,
  type ClientWorkspaceStats,
} from '@/lib/api/clients';
import { formatAmountSr } from '@/lib/formatters';
import { useOrgPath } from '@/lib/navigation';
import type { ClientResponse, ClientUpdate } from '@/lib/types/client';

interface PageProps {
  params: Promise<{ orgSlug: string; clientId: string }>;
}

export default function ClientWorkspacePage({ params }: PageProps) {
  const { orgSlug, clientId } = use(params);
  const searchParams = useSearchParams();
  const t = useTranslations('clientWorkspace');
  const tClients = useTranslations('clients');
  const tCommon = useTranslations('common');
  const orgPath = useOrgPath();
  const { hasRole } = useAuth();

  const activeTab = (searchParams.get('tab') as TabKey | null) ?? 'timeline';

  const [client, setClient] = useState<ClientResponse | null>(null);
  const [stats, setStats] = useState<ClientWorkspaceStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [c, s] = await Promise.all([
        fetchClient(clientId),
        fetchClientWorkspaceStats(clientId).catch(() => null),
      ]);
      setClient(c);
      setStats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  async function handleSave(data: ClientUpdate) {
    setSaving(true);
    try {
      const updated = await updateClient(clientId, data);
      setClient(updated);
      setEditOpen(false);
      setToast({ message: tClients('editSuccess'), type: 'success' });
    } catch {
      setToast({ message: tClients('saveError'), type: 'error' });
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleActive() {
    if (!client) return;
    try {
      const result = await toggleClientActive(clientId);
      setClient({ ...client, is_active: result.is_active });
      setToast({
        message: result.is_active ? tClients('editSuccess') : tClients('deleteSuccess'),
        type: 'success',
      });
    } catch {
      setToast({ message: tClients('saveError'), type: 'error' });
    }
  }

  if (error) {
    return (
      <div className="mx-auto w-full max-w-[100rem]">
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-[100rem] space-y-5 sm:space-y-7 lg:space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-stone-500">
        <Link href={orgPath('/klijenti')} className="hover:text-violet-700 transition-colors">
          {t('breadcrumbClients')}
        </Link>
        <span className="text-stone-300">/</span>
        <span className="text-stone-700 font-medium">{client?.name ?? tCommon('loading')}</span>
      </nav>

      {/* Hero header — single row at every breakpoint: avatar+name on the
          left, edit/kebab pinned to the far right. */}
      <header className="flex flex-row items-start justify-between gap-3 sm:gap-4 lg:gap-6">
        <div className="flex items-start gap-3 sm:gap-4 min-w-0 flex-1">
          {client ? (
            <ClientAvatar name={client.name} seed={client.id} size="xl" />
          ) : (
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-stone-100 animate-pulse" />
          )}
          <div className="min-w-0 flex-1 pt-1">
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-stone-900 tracking-tight leading-tight break-words min-w-0">
                {client?.name ?? '…'}
              </h1>
              {client && !client.is_active && (
                <span className="inline-flex items-center px-2.5 py-1 text-xs font-semibold text-stone-600 bg-stone-100 rounded-full">
                  {t('inactive')}
                </span>
              )}
            </div>
            {client && (
              <div className="flex items-center gap-1.5 flex-wrap mt-3">
                <MetaChip label="PIB" value={client.pib} />
                {client.mb && <MetaChip label="MB" value={client.mb} />}
                {client.city && <MetaChip value={client.city} />}
                {client.contact_email && <MetaChip value={client.contact_email} />}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {hasRole('manager') && client && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setEditOpen(true)}
                aria-label={tCommon('edit')}
                className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-2 text-sm font-medium text-stone-700 bg-white ring-1 ring-stone-200 rounded-lg hover:bg-stone-50 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <span className="hidden sm:inline">{tCommon('edit')}</span>
              </button>
              <ClientKebab
                isActive={client.is_active}
                onToggleActive={handleToggleActive}
              />
            </div>
          )}
        </div>
      </header>

      {/* Health strip */}
      <HealthStrip stats={stats} isLoading={isLoading} />

      {/* Tab bar */}
      <TabBar activeTab={activeTab} clientId={clientId} orgSlug={orgSlug} />

      {/* Tab content */}
      <div>
        {activeTab === 'timeline' && (
          <ClientTimeline clientId={clientId} />
        )}
        {activeTab === 'fakture' && (
          <ClientInvoices clientId={clientId} />
        )}
        {activeTab === 'izvestaji' && (
          <ReportsSurface clientId={clientId} />
        )}
        {activeTab === 'pravila' && <ClientRules clientId={clientId} />}
      </div>

      {/* Edit modal */}
      {editOpen && client && (
        <ClientModal
          client={client}
          saving={saving}
          onSave={(data) => handleSave(data as ClientUpdate)}
          onClose={() => setEditOpen(false)}
        />
      )}

      {/* Toast */}
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

function MetaChip({ label, value }: { label?: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-stone-100 text-[11px] font-medium text-stone-600 tabular-nums">
      {label && <span className="text-stone-400">{label}</span>}
      <span className="text-stone-700">{value}</span>
    </span>
  );
}

function HealthStrip({
  stats,
  isLoading,
}: {
  stats: ClientWorkspaceStats | null;
  isLoading: boolean;
}) {
  const t = useTranslations('clientWorkspace');

  if (isLoading && !stats) {
    return (
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-16 sm:h-20 rounded-2xl bg-white ring-1 ring-stone-200/80 animate-pulse" />
        ))}
      </div>
    );
  }
  if (!stats) return null;

  const needsAttention = stats.pending_count > 0 || stats.blocked_count > 0;

  // Always 3 columns: with only 3 tiles a 2+1 split on mobile leaves an
  // awkward orphan; equal thirds reads cleaner and the tile padding
  // shrinks below to keep numbers legible at 375px.
  return (
    <div className="grid grid-cols-3 gap-2 sm:gap-3">
      <StatTile
        label={t('tileInvoices')}
        value={stats.invoice_count}
        accent="neutral"
        hint={
          stats.total_amount > 0
            ? formatAmountSr(String(stats.total_amount), 'RSD')
            : undefined
        }
      />
      <StatTile
        label={t('tilePending')}
        value={stats.pending_count}
        accent={stats.pending_count > 0 ? 'amber' : 'neutral'}
      />
      <StatTile
        label={t('tileBlocked')}
        value={stats.blocked_count}
        accent={stats.blocked_count > 0 ? 'rose' : needsAttention ? 'neutral' : 'emerald'}
      />
    </div>
  );
}

const TILE_ACCENTS = {
  neutral: 'bg-white ring-1 ring-stone-200/80',
  amber: 'bg-amber-50/60 ring-1 ring-amber-200',
  rose: 'bg-rose-50/60 ring-1 ring-rose-200',
  emerald: 'bg-emerald-50/60 ring-1 ring-emerald-200',
} as const;

function StatTile({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: number;
  hint?: string;
  accent: keyof typeof TILE_ACCENTS;
}) {
  return (
    <div className={`rounded-2xl p-3 sm:p-4 min-w-0 ${TILE_ACCENTS[accent]}`}>
      <p className="text-[10px] sm:text-[11px] font-semibold text-stone-500 uppercase tracking-wider truncate">{label}</p>
      <p className="mt-1 text-xl sm:text-2xl font-bold text-stone-900 tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-[11px] sm:text-xs text-stone-500 tabular-nums truncate">{hint}</p>}
    </div>
  );
}

function ClientKebab({
  isActive,
  onToggleActive,
}: {
  isActive: boolean;
  onToggleActive: () => void;
}) {
  const tClients = useTranslations('clients');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [open]);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((p) => !p);
        }}
        aria-label="Više opcija"
        className="p-2 text-stone-500 bg-white ring-1 ring-stone-200 rounded-lg hover:bg-stone-50 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg ring-1 ring-stone-200 z-30 overflow-hidden">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onToggleActive();
            }}
            className="w-full text-left px-3 py-2 text-sm text-stone-700 hover:bg-stone-50 transition-colors"
          >
            {isActive ? tClients('inactive') : tClients('active')}
          </button>
        </div>
      )}
    </div>
  );
}

