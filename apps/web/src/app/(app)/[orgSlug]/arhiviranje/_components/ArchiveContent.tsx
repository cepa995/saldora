'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  fetchExportHistory,
  fetchArchiveSettings,
  triggerArchiveExport,
  type ExportLog,
  type ArchiveSettings,
} from '@/lib/api/archive';
import { fetchAuditExportHistory, previewAuditExport } from '@/lib/api/audit-export';
import { formatDateSr, formatRelativeTime, formatFileSize } from '@/lib/formatters';
import { isPlanError } from '@/lib/api-client';
import { UpgradeModal, type PlanErrorInfo } from '@/components/UpgradeModal';
import type { AuditExportResponse } from '@/lib/types/audit-export';

// ── Unified history item ───────────────────────────────────────────

interface HistoryItem {
  id: string;
  created_at: string;
  period: string;
  invoice_count: number | null;
  file_size: number | null;
  status: string;
  delivered_to: string | null;
  download_url: string | null;
  reason: string | null;
}

function normalizeExportLog(item: ExportLog): HistoryItem {
  return {
    id: `export-${item.id}`,
    created_at: item.delivered_at,
    period: item.period,
    invoice_count: item.invoice_count,
    file_size: item.file_size_bytes,
    status: item.status,
    delivered_to: item.delivered_to || null,
    download_url: item.download_url ?? null,
    reason: item.reason ?? null,
  };
}

function normalizeAuditExport(item: AuditExportResponse): HistoryItem {
  return {
    id: `audit-${item.id}`,
    created_at: item.created_at,
    period: `${formatDateSr(item.period.from)} — ${formatDateSr(item.period.to)}`,
    invoice_count: item.invoice_count,
    file_size: item.file_size,
    status: item.status,
    delivered_to: null,
    download_url: item.status === 'ready' ? item.download_url : null,
    reason: item.reason,
  };
}

// ── Status badge styles ────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  delivered: 'bg-green-50 text-green-700 ring-green-600/20',
  ready: 'bg-green-50 text-green-700 ring-green-600/20',
  processing: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  failed: 'bg-red-50 text-red-700 ring-red-600/20',
  expired: 'bg-gray-100 text-gray-500 ring-gray-400/20',
  skipped: 'bg-gray-100 text-gray-500 ring-gray-400/20',
};

function statusLabel(status: string, tArchive: (k: string) => string, tAudit: (k: string) => string): string {
  switch (status) {
    case 'delivered': return tArchive('delivered');
    case 'ready': return tAudit('statusReady');
    case 'processing': return tAudit('statusProcessing');
    case 'failed': return tArchive('failed');
    case 'expired': return tAudit('statusExpired');
    case 'skipped': return tArchive('skipped');
    default: return status;
  }
}

// ── Helpers ─────────────────────────────────────────────────────────

function getDefaultDateRange(): { from: string; to: string } {
  const now = new Date();
  const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
  const from = `${prevMonth.getFullYear()}-${String(prevMonth.getMonth() + 1).padStart(2, '0')}-${String(prevMonth.getDate()).padStart(2, '0')}`;
  const to = `${lastDay.getFullYear()}-${String(lastDay.getMonth() + 1).padStart(2, '0')}-${String(lastDay.getDate()).padStart(2, '0')}`;
  return { from, to };
}

function derivePeriod(dateFrom: string): string {
  return dateFrom.slice(0, 7);
}

// ── History Row (Desktop) ──────────────────────────────────────────

function HistoryRow({
  item,
  tArchive,
  tAudit,
}: {
  item: HistoryItem;
  tArchive: (key: string) => string;
  tAudit: (key: string) => string;
}) {
  return (
    <tr className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50">
      <td className="px-3 py-2.5 text-sm text-gray-600">{formatRelativeTime(item.created_at)}</td>
      <td className="px-3 py-2.5 text-sm text-gray-900 font-medium">{item.period}</td>
      <td className="px-3 py-2.5 text-sm text-gray-600 text-center">{item.invoice_count ?? '—'}</td>
      <td className="px-3 py-2.5 text-sm text-gray-600">{formatFileSize(item.file_size)}</td>
      <td className="px-3 py-2.5">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${STATUS_STYLES[item.status] || STATUS_STYLES.skipped}`}
        >
          {statusLabel(item.status, tArchive, tAudit)}
        </span>
      </td>
      <td className="px-3 py-2.5 text-sm text-gray-500 max-w-[160px] truncate">{item.delivered_to || '—'}</td>
      <td className="px-3 py-2.5">
        {item.download_url ? (
          <a
            href={item.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {tAudit('download')}
          </a>
        ) : item.status === 'processing' ? (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600">
            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {tAudit('statusProcessing')}
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
    </tr>
  );
}

// ── History Card (Mobile) ──────────────────────────────────────────

function HistoryCard({
  item,
  tArchive,
  tAudit,
}: {
  item: HistoryItem;
  tArchive: (key: string) => string;
  tAudit: (key: string) => string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-900">{item.period}</span>
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${STATUS_STYLES[item.status] || STATUS_STYLES.skipped}`}
        >
          {statusLabel(item.status, tArchive, tAudit)}
        </span>
      </div>
      <div className="flex gap-4 text-xs text-gray-500">
        <span>{formatRelativeTime(item.created_at)}</span>
        <span>{item.invoice_count ?? '—'} faktura</span>
        <span>{formatFileSize(item.file_size)}</span>
      </div>
      {item.delivered_to && (
        <p className="text-xs text-gray-400 truncate">{item.delivered_to}</p>
      )}
      {item.download_url && (
        <a
          href={item.download_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 w-full px-3 py-1.5 text-xs font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {tAudit('download')}
        </a>
      )}
    </div>
  );
}

// ── ArchiveContent ─────────────────────────────────────────────────

export default function ArchiveContent() {
  const tArchive = useTranslations('archive');
  const tAudit = useTranslations('audit');

  const defaults = getDefaultDateRange();
  const [dateFrom, setDateFrom] = useState(defaults.from);
  const [dateTo, setDateTo] = useState(defaults.to);
  const [reason, setReason] = useState('');
  const [generating, setGenerating] = useState(false);
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ message: string; ok: boolean } | null>(null);

  const [archiveSettings, setArchiveSettings] = useState<ArchiveSettings | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(true);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');

  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);

  // ── Load settings ──────────────────────────────────────────────

  useEffect(() => {
    fetchArchiveSettings()
      .then(setArchiveSettings)
      .catch(() => {})
      .finally(() => setSettingsLoading(false));
  }, []);

  // ── Load merged history ────────────────────────────────────────

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const [exportLogs, auditLogs] = await Promise.all([
        fetchExportHistory().catch(() => [] as ExportLog[]),
        fetchAuditExportHistory().catch((err) => {
          if (isPlanError(err)) {
            setPlanError(err.planError as PlanErrorInfo);
          }
          return [] as AuditExportResponse[];
        }),
      ]);

      const merged: HistoryItem[] = [
        ...(Array.isArray(exportLogs) ? exportLogs : []).map(normalizeExportLog),
        ...(Array.isArray(auditLogs) ? auditLogs : []).map(normalizeAuditExport),
      ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setHistory(merged);
    } catch {
      setHistoryError(tAudit('errorHistory'));
    } finally {
      setHistoryLoading(false);
    }
  }, [tAudit]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // ── Debounced preview count ────────────────────────────────────

  useEffect(() => {
    if (!dateFrom || !dateTo || dateFrom > dateTo) {
      setPreviewCount(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const result = await previewAuditExport(dateFrom, dateTo);
        if (!cancelled) setPreviewCount(result.invoice_count);
      } catch {
        if (!cancelled) setPreviewCount(null);
      }
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [dateFrom, dateTo]);

  // ── Generate handler ───────────────────────────────────────────

  async function handleGenerate() {
    setError('');
    if (!dateFrom || !dateTo) { setError(tAudit('errorDateRequired')); return; }
    if (dateFrom > dateTo) { setError(tAudit('errorDateRange')); return; }

    setGenerating(true);
    try {
      const period = derivePeriod(dateFrom);
      await triggerArchiveExport(period);
      setToast({ message: tArchive('exportQueued'), ok: true });
      setTimeout(() => setToast(null), 5000);
      setReason('');
      // Auto-refresh history after background task has time to complete
      setTimeout(() => loadHistory(), 10000);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setToast({ message: tArchive('exportFailed'), ok: false });
        setTimeout(() => setToast(null), 4000);
      }
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      {/* Error alert */}
      {error && (
        <div className="mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-500 hover:text-red-700 ml-3 shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Two-column layout: Form + Info */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
        {/* Left: Generate form (3/5) */}
        <div className="lg:col-span-3 bg-white border border-gray-200 rounded-xl p-4 min-w-0 overflow-hidden">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">{tAudit('sectionGenerate')}</h2>

          {/* Date range */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div className="min-w-0">
              <label htmlFor="dateFrom" className="block text-xs font-medium text-gray-600 mb-1">
                {tAudit('dateFrom')}
              </label>
              <input
                id="dateFrom"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="block w-full min-w-0 px-2.5 py-2 border border-gray-300 rounded-lg text-base sm:text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-500"
              />
            </div>
            <div className="min-w-0">
              <label htmlFor="dateTo" className="block text-xs font-medium text-gray-600 mb-1">
                {tAudit('dateTo')}
              </label>
              <input
                id="dateTo"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="block w-full min-w-0 px-2.5 py-2 border border-gray-300 rounded-lg text-base sm:text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-500"
              />
            </div>
          </div>

          {/* Preview count hint */}
          {previewCount !== null && (
            <p className={`text-xs mb-2 ${previewCount === 0 ? 'text-amber-600 font-medium' : 'text-gray-500'}`}>
              {previewCount === 0
                ? tAudit('previewEmpty')
                : tAudit('previewCount', { count: String(previewCount) })}
            </p>
          )}

          {/* Reason field */}
          <div className="mb-3">
            <label htmlFor="reason" className="block text-xs font-medium text-gray-600 mb-1">
              {tAudit('reason')}
            </label>
            <input
              id="reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={tAudit('reasonPlaceholder')}
              className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-500"
            />
          </div>

          {/* Archive contents info */}
          <div className="border-t border-gray-100 pt-3 mb-3">
            <p className="text-xs font-medium text-gray-500 mb-1.5">{tArchive('archiveContents')}</p>
            <ul className="text-xs text-gray-600 space-y-1">
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 bg-violet-400 rounded-full" />
                {tArchive('contentRegister')}
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 bg-violet-400 rounded-full" />
                {tArchive('contentVat')}
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 bg-violet-400 rounded-full" />
                {tArchive('contentAudit')}
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 bg-violet-400 rounded-full" />
                {tArchive('contentPdfs')}
              </li>
            </ul>
          </div>

          {/* Delivery email */}
          {!settingsLoading && archiveSettings?.email && (
            <div className="border-t border-gray-100 pt-3 mb-3">
              <p className="text-xs font-medium text-gray-500 mb-1">{tArchive('deliveryEmail')}</p>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-900 font-medium truncate">
                  {archiveSettings.email}
                </span>
                <span className="text-xs text-gray-400 shrink-0">{tArchive('changeEmail')}</span>
              </div>
            </div>
          )}

          {/* Generate button */}
          <div className="pt-3 border-t border-gray-100 flex justify-end">
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating && (
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {generating ? tArchive('generating') : 'Izvezi odmah'}
            </button>
          </div>
        </div>

        {/* Right: Info panels (2/5) */}
        <div className="lg:col-span-2 space-y-3">
          {/* What's included */}
          <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-violet-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="text-sm font-semibold text-violet-900">{tAudit('infoTitle')}</h3>
            </div>
            <ul className="space-y-1">
              {(['infoItem1', 'infoItem2', 'infoItem3', 'infoItem4'] as const).map((key) => (
                <li key={key} className="flex items-start gap-1.5 text-xs text-violet-700">
                  <span className="shrink-0 mt-1.5 w-1 h-1 rounded-full bg-violet-400" />
                  {tAudit(key)}
                </li>
              ))}
            </ul>
          </div>

          {/* Tips */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-amber-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h3 className="text-sm font-semibold text-amber-900">{tAudit('tipsTitle')}</h3>
            </div>
            <ul className="space-y-1.5">
              <li className="text-xs text-amber-700">{tAudit('tipAuditTrail')}</li>
              <li className="text-xs text-amber-700">{tAudit('tipDocumentsSize')}</li>
            </ul>
          </div>

          {/* Expiry note */}
          <div className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-50 border border-gray-200">
            <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs text-gray-500">{tAudit('infoExpiry')}</span>
          </div>
        </div>
      </div>

      {/* History section — full width */}
      <div>
        <h2 className="text-sm font-semibold text-gray-900 mb-2">{tAudit('sectionHistory')}</h2>

        {historyLoading ? (
          <div className="flex items-center justify-center py-8">
            <svg className="w-5 h-5 animate-spin text-violet-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        ) : historyError ? (
          <div className="text-center py-8">
            <p className="text-sm text-red-500">{historyError}</p>
            <button
              onClick={loadHistory}
              className="mt-1 text-sm text-violet-600 hover:text-violet-700 underline"
            >
              Pokusaj ponovo
            </button>
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-8 bg-white border border-gray-200 rounded-xl">
            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-2">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <p className="text-sm text-gray-500">{tAudit('historyEmpty')}</p>
            <p className="text-xs text-gray-400 mt-0.5">{tAudit('historyEmptySubtitle')}</p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden sm:block bg-white border border-gray-200 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50/50">
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnDate')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnPeriod')}</th>
                    <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnInvoiceCount')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnFileSize')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnStatus')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('deliveredTo')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <HistoryRow key={item.id} item={item} tArchive={tArchive} tAudit={tAudit} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="sm:hidden space-y-2">
              {history.map((item) => (
                <HistoryCard key={item.id} item={item} tArchive={tArchive} tAudit={tAudit} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl shadow-lg ${toast.ok ? 'bg-gray-900 text-white' : 'bg-red-600 text-white'}`}>
          {toast.ok ? (
            <svg className="w-4 h-4 text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-red-200 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          {toast.message}
        </div>
      )}

      {/* Upgrade modal */}
      {planError && (
        <UpgradeModal error={planError} onClose={() => setPlanError(null)} />
      )}
    </div>
  );
}
