'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { ClientTimeline } from '@/components/client-workspace/ClientTimeline';
import { MonthPicker } from '@/components/client-workspace/MonthPicker';
import { TabBar, type TabKey } from '@/components/client-workspace/TabBar';
import { fetchClient } from '@/lib/api/clients';
import { useOrgPath } from '@/lib/navigation';
import type { ClientResponse } from '@/lib/types/client';

interface PageProps {
  params: Promise<{ orgSlug: string; clientId: string }>;
}

function currentYYYYMM(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export default function ClientWorkspacePage({ params }: PageProps) {
  const { orgSlug, clientId } = use(params);
  const searchParams = useSearchParams();
  const t = useTranslations('clientWorkspace');
  const tCommon = useTranslations('common');
  const orgPath = useOrgPath();

  const activeTab = (searchParams.get('tab') as TabKey | null) ?? 'timeline';
  const [period, setPeriod] = useState<string>(currentYYYYMM());

  const [client, setClient] = useState<ClientResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setClient(await fetchClient(clientId));
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  const headerMeta = useMemo(() => {
    if (!client) return null;
    return [
      client.pib ? `PIB ${client.pib}` : null,
      client.mb ? `MB ${client.mb}` : null,
      client.city ?? null,
    ].filter(Boolean);
  }, [client]);

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-gray-500">
        <Link href={orgPath('/klijenti')} className="hover:text-violet-700 transition-colors">
          {t('breadcrumbClients')}
        </Link>
        <span className="text-gray-300">/</span>
        <span className="text-gray-900 font-medium">
          {client?.name ?? tCommon('loading')}
        </span>
      </nav>

      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
              {client?.name ?? '…'}
            </h1>
            {!client?.is_active && (
              <span className="inline-flex items-center px-2.5 py-1 text-xs font-semibold text-gray-600 bg-gray-100 rounded-full">
                {t('inactive')}
              </span>
            )}
          </div>
          {headerMeta && headerMeta.length > 0 && (
            <p className="text-sm text-gray-500 mt-1 flex items-center gap-3 flex-wrap">
              {headerMeta.map((bit, i) => (
                <span key={i} className="after:content-['·'] after:ml-3 after:text-gray-300 last:after:content-['']">
                  {bit}
                </span>
              ))}
            </p>
          )}
        </div>

        <MonthPicker value={period} onChange={setPeriod} />
      </header>

      {/* Tab bar */}
      <TabBar activeTab={activeTab} clientId={clientId} orgSlug={orgSlug} />

      {/* Tab content */}
      <div>
        {activeTab === 'timeline' && (
          <ClientTimeline clientId={clientId} period={period} />
        )}
        {activeTab === 'fakture' && (
          <TabPlaceholder
            title={t('tabFakture')}
            description={t('tabFaktureHint')}
            href={orgPath(`/invoices?client_id=${clientId}`)}
            ctaLabel={t('openFeaturePage')}
            isLoading={isLoading}
          />
        )}
        {activeTab === 'izvestaji' && (
          <TabPlaceholder
            title={t('tabIzvestaji')}
            description={t('tabIzvestajiHint')}
            href={orgPath(`/izvestaji?client_id=${clientId}`)}
            ctaLabel={t('openFeaturePage')}
            isLoading={isLoading}
          />
        )}
        {activeTab === 'pravila' && (
          <TabPlaceholder
            title={t('tabPravila')}
            description={t('tabPravilaHint')}
            href={orgPath(`/rules?client_id=${clientId}`)}
            ctaLabel={t('openFeaturePage')}
            isLoading={isLoading}
          />
        )}
      </div>
    </div>
  );
}

function TabPlaceholder({
  title,
  description,
  href,
  ctaLabel,
  isLoading,
}: {
  title: string;
  description: string;
  href: string;
  ctaLabel: string;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-10 animate-pulse">
        <div className="h-5 bg-gray-100 rounded w-1/3 mb-3" />
        <div className="h-4 bg-gray-100 rounded w-2/3" />
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-8 sm:p-10">
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{title}</h2>
      <p className="text-sm text-gray-500 max-w-lg">{description}</p>
      <Link
        href={href}
        className="mt-5 inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
      >
        {ctaLabel}
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
        </svg>
      </Link>
    </div>
  );
}
