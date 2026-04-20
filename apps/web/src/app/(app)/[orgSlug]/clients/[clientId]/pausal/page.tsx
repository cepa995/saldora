'use client';

import Link from 'next/link';
import { use, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchClient } from '@/lib/api/clients';
import {
  fetchInvoicePdfUrl,
  fetchKPOEntries,
  fetchOutgoingInvoices,
  fetchRevenueStatus,
} from '@/lib/api/pausal';
import type { ClientResponse } from '@/lib/types/client';
import type {
  KPOEntry,
  RevenueStatusResponse,
} from '@/lib/types/pausal';
import type { OutgoingInvoiceListResponse } from '@/lib/api/pausal';

import { IssueInvoiceModal } from '@/components/pausal/IssueInvoiceModal';
import { RevenueStatusCard } from '@/components/pausal/RevenueStatusCard';

interface PageProps {
  params: Promise<{ orgSlug: string; clientId: string }>;
}

function fmtRsd(amount: string | null | undefined): string {
  if (!amount) return '—';
  const n = Number(amount);
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('sr-Latn-RS', {
    maximumFractionDigits: 0,
  }).format(Math.round(n));
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('sr-Latn-RS', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export default function PausalClientDashboardPage({ params }: PageProps) {
  const { orgSlug, clientId } = use(params);
  const t = useTranslations('pausal');
  const tCommon = useTranslations('common');

  const currentYear = useMemo(() => new Date().getFullYear(), []);
  const [year, setYear] = useState<number>(currentYear);

  const [client, setClient] = useState<ClientResponse | null>(null);
  const [revenue, setRevenue] = useState<RevenueStatusResponse | null>(null);
  const [kpo, setKpo] = useState<KPOEntry[]>([]);
  const [outgoing, setOutgoing] = useState<OutgoingInvoiceListResponse['data']>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showIssueModal, setShowIssueModal] = useState(false);

  const loadAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [c, r, k, inv] = await Promise.all([
        fetchClient(clientId),
        fetchRevenueStatus(clientId, year),
        fetchKPOEntries(clientId, { year, per_page: 10 }),
        fetchOutgoingInvoices(clientId, { per_page: 10 }),
      ]);
      setClient(c);
      setRevenue(r);
      setKpo(k.data);
      setOutgoing(inv.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, year, tCommon]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  async function handleDownloadPdf(invoiceId: string) {
    try {
      const { url } = await fetchInvoicePdfUrl(clientId, invoiceId);
      window.open(url, '_blank');
    } catch {
      /* no-op */
    }
  }

  function handleIssued() {
    // Refresh the full dashboard after issuance.
    void loadAll();
  }

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <nav className="text-xs text-gray-500 mb-2 flex items-center gap-2">
            <Link
              href={`/${orgSlug}/clients`}
              className="hover:text-violet-700"
            >
              {tCommon('back')}
            </Link>
            <span>/</span>
            <span className="text-gray-900 font-medium">
              {client?.name ?? '…'}
            </span>
          </nav>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
              {client?.name ?? '…'}
            </h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200 ring-inset rounded-full">
              {t('pausalacBadge')}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1 flex items-center gap-3 flex-wrap">
            {client?.pib && <span>PIB {client.pib}</span>}
            {client?.activity_code && (
              <span>
                <span className="text-gray-400 mr-1">·</span>
                {t('colActivity')} {client.activity_code}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
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
          <button
            type="button"
            onClick={() => setShowIssueModal(true)}
            disabled={!client}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-violet-600 to-indigo-600 rounded-lg hover:from-violet-700 hover:to-indigo-700 shadow-sm shadow-violet-500/20 transition-all disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {t('issueInvoice')}
          </button>
        </div>
      </header>

      {/* Revenue card + Calendar placeholder */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <RevenueStatusCard data={revenue} isLoading={isLoading} />
        </div>
        <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-violet-100 text-violet-700 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="font-semibold text-gray-900">{t('calendarPlaceholderTitle')}</h3>
          </div>
          <p className="text-sm text-gray-500 flex-1">
            {t('calendarPlaceholderBody')}
          </p>
          <span className="mt-4 inline-flex self-start items-center gap-1.5 px-2 py-1 text-xs font-medium text-violet-700 bg-violet-50 rounded-full">
            <span className="w-1.5 h-1.5 bg-violet-500 rounded-full" />
            {t('calendarPlaceholderHint')}
          </span>
        </div>
      </div>

      {/* KPO entries */}
      <section className="rounded-2xl border border-gray-100 bg-white shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 px-5 sm:px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="font-semibold text-gray-900">{t('recentKPO')}</h2>
            <p className="text-xs text-gray-500 mt-0.5">{t('recentKPOSubtitle')}</p>
          </div>
        </div>
        {isLoading && kpo.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            {tCommon('loading')}
          </div>
        ) : kpo.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-sm text-gray-500">{t('noKPO')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 uppercase tracking-wider">
                  <th className="text-left px-5 sm:px-6 py-3 font-medium">{t('entryNumber')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('entryDate')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('customer')}</th>
                  <th className="text-right px-5 sm:px-6 py-3 font-medium">{t('amount')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {kpo.map((entry) => (
                  <tr
                    key={entry.id}
                    className={entry.is_cancelled ? 'text-gray-400 line-through' : ''}
                  >
                    <td className="px-5 sm:px-6 py-3 font-semibold tabular-nums">
                      {entry.entry_number}
                    </td>
                    <td className="px-4 py-3 text-gray-600 tabular-nums">
                      {fmtDate(entry.entry_date)}
                    </td>
                    <td className="px-4 py-3 text-gray-900">
                      <div className="flex items-center gap-2">
                        <span>{entry.customer_name}</span>
                        {entry.storno_of_id && (
                          <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200">
                            STORNO
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 sm:px-6 py-3 text-right tabular-nums font-medium">
                      {fmtRsd(entry.amount)}{' '}
                      <span className="text-xs text-gray-400">{entry.currency}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Issued invoices */}
      <section className="rounded-2xl border border-gray-100 bg-white shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 px-5 sm:px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="font-semibold text-gray-900">{t('issuedInvoicesTitle')}</h2>
            <p className="text-xs text-gray-500 mt-0.5">{t('issuedInvoicesSubtitle')}</p>
          </div>
        </div>
        {isLoading && outgoing.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            {tCommon('loading')}
          </div>
        ) : outgoing.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-sm text-gray-500 mb-3">{t('noInvoices')}</p>
            <button
              type="button"
              onClick={() => setShowIssueModal(true)}
              disabled={!client}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {t('noInvoicesCta')}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 uppercase tracking-wider">
                  <th className="text-left px-5 sm:px-6 py-3 font-medium">{t('invoiceNumber')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('issuedAt')}</th>
                  <th className="text-right px-4 py-3 font-medium">{t('total')}</th>
                  <th className="text-right px-5 sm:px-6 py-3 font-medium w-32">
                    {tCommon('actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {outgoing.map((inv) => (
                  <tr key={inv.id}>
                    <td className="px-5 sm:px-6 py-3 font-semibold tabular-nums">
                      {inv.invoice_number ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-600 tabular-nums">
                      {fmtDate(inv.invoice_date)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">
                      {fmtRsd(inv.total_amount)}{' '}
                      <span className="text-xs text-gray-400">{inv.currency}</span>
                    </td>
                    <td className="px-5 sm:px-6 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleDownloadPdf(inv.id)}
                        className="text-xs font-semibold text-violet-700 hover:text-violet-900"
                      >
                        {t('downloadPdf')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showIssueModal && client && (
        <IssueInvoiceModal
          paušalac={client}
          onClose={() => setShowIssueModal(false)}
          onIssued={handleIssued}
        />
      )}
    </div>
  );
}
