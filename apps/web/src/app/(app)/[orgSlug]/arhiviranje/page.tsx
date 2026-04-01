'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { AccessDenied } from '@/components';
import { createAuditExport, fetchAuditExportHistory, previewAuditExport } from '@/lib/api/audit-export';
import {
  fetchExportHistory,
  fetchArchiveSettings,
  updateArchiveSettings,
  triggerArchiveExport,
  type ExportLog,
  type ArchiveSettings,
} from '@/lib/api/archive';
import { formatDateSr, formatRelativeTime, formatFileSize } from '@/lib/formatters';
import { isPlanError } from '@/lib/api-client';
import { UpgradeModal, type PlanErrorInfo } from '@/components/UpgradeModal';
import type { AuditExportResponse } from '@/lib/types/audit-export';

// ── Status badge styles (audit export) ─────────────────────────────

const AUDIT_STATUS_STYLES: Record<string, string> = {
  processing: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  ready: 'bg-green-50 text-green-700 ring-green-600/20',
  expired: 'bg-gray-100 text-gray-500 ring-gray-400/20',
};

// ── Archive delivery status styles ──────────────────────────────────

const ARCHIVE_STATUS_STYLES: Record<string, string> = {
  delivered: 'bg-green-50 text-green-700 ring-green-600/20',
  failed: 'bg-red-50 text-red-700 ring-red-600/20',
  skipped: 'bg-gray-100 text-gray-500 ring-gray-400/20',
};

// ── Content Toggle ──────────────────────────────────────────────────

function ContentToggle({
  checked,
  onChange,
  disabled,
  title,
  description,
  badge,
}: {
  checked: boolean;
  onChange?: (val: boolean) => void;
  disabled?: boolean;
  title: string;
  description: string;
  badge?: string;
}) {
  return (
    <label
      className={`flex items-center gap-2.5 py-2 ${disabled ? 'opacity-60' : 'cursor-pointer'}`}
    >
      <div className="relative shrink-0">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.checked)}
          className="sr-only peer"
        />
        <div
          className={`w-8 h-[18px] rounded-full transition-colors ${
            disabled
              ? 'bg-violet-300'
              : 'bg-gray-200 peer-checked:bg-violet-600 peer-focus:ring-2 peer-focus:ring-violet-300'
          } after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:after:translate-x-3.5`}
        />
      </div>
      <span className="text-sm text-gray-700 leading-tight">
        {title}
        {badge && (
          <span className="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20">
            {badge}
          </span>
        )}
      </span>
      <span className="hidden lg:inline text-xs text-gray-400 ml-auto truncate max-w-[180px]">
        {description}
      </span>
    </label>
  );
}

// ── Audit History Row (Desktop) ─────────────────────────────────────

function AuditHistoryRow({
  item,
  t,
}: {
  item: AuditExportResponse;
  t: (key: string, values?: Record<string, string>) => string;
}) {
  const statusKey = `status${item.status.charAt(0).toUpperCase() + item.status.slice(1)}` as
    | 'statusProcessing'
    | 'statusReady'
    | 'statusExpired';

  return (
    <tr className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50">
      <td className="px-3 py-2.5 text-sm text-gray-600">{formatRelativeTime(item.created_at)}</td>
      <td className="px-3 py-2.5 text-sm text-gray-900">
        {formatDateSr(item.period.from)} — {formatDateSr(item.period.to)}
      </td>
      <td className="px-3 py-2.5 text-sm text-gray-600 text-center">{item.invoice_count ?? '—'}</td>
      <td className="px-3 py-2.5 text-sm text-gray-600">{formatFileSize(item.file_size)}</td>
      <td className="px-3 py-2.5">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${AUDIT_STATUS_STYLES[item.status] || AUDIT_STATUS_STYLES.expired}`}
        >
          {t(statusKey)}
        </span>
      </td>
      <td className="px-3 py-2.5 text-sm text-gray-500 max-w-[140px] truncate">{item.reason || '—'}</td>
      <td className="px-3 py-2.5">
        {item.status === 'ready' && item.download_url ? (
          <a
            href={item.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {t('download')}
          </a>
        ) : item.status === 'processing' ? (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600">
            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {t('statusProcessing')}
          </span>
        ) : (
          <span className="text-xs text-gray-400">{t('downloadExpired')}</span>
        )}
      </td>
    </tr>
  );
}

// ── Audit History Card (Mobile) ─────────────────────────────────────

function AuditHistoryCard({
  item,
  t,
}: {
  item: AuditExportResponse;
  t: (key: string, values?: Record<string, string>) => string;
}) {
  const statusKey = `status${item.status.charAt(0).toUpperCase() + item.status.slice(1)}` as
    | 'statusProcessing'
    | 'statusReady'
    | 'statusExpired';

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-900">
          {formatDateSr(item.period.from)} — {formatDateSr(item.period.to)}
        </span>
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${AUDIT_STATUS_STYLES[item.status] || AUDIT_STATUS_STYLES.expired}`}
        >
          {t(statusKey)}
        </span>
      </div>
      <div className="flex gap-4 text-xs text-gray-500">
        <span>{formatRelativeTime(item.created_at)}</span>
        <span>{item.invoice_count ?? '—'} faktura</span>
        <span>{formatFileSize(item.file_size)}</span>
      </div>
      {item.status === 'ready' && item.download_url && (
        <a
          href={item.download_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 w-full px-3 py-1.5 text-xs font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {t('download')}
        </a>
      )}
    </div>
  );
}

// ── Period Picker Modal ─────────────────────────────────────────────

function PeriodPickerModal({
  onConfirm,
  onClose,
  generating,
  tArchive,
}: {
  onConfirm: (period: string) => void;
  onClose: () => void;
  generating: boolean;
  tArchive: (key: string) => string;
}) {
  const now = new Date();
  const defaultPeriod = `${now.getFullYear()}-${String(now.getMonth()).padStart(2, '0')}`;
  const [period, setPeriod] = useState(defaultPeriod);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-1">{tArchive('testNow')}</h3>
        <p className="text-xs text-gray-500 mb-4">{tArchive('selectPeriod')}</p>
        <input
          type="month"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          max={defaultPeriod}
          className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-500 mb-4"
        />
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            disabled={generating}
            className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            Otkaži
          </button>
          <button
            onClick={() => onConfirm(period)}
            disabled={!period || generating}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating && (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {generating ? tArchive('generating') : tArchive('testNow')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────

export default function ArhiviranjePage() {
  const tArchive = useTranslations('archive');
  const tAudit = useTranslations('audit');
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  // ── Monthly archive section state ───────────────────────────────
  const [archiveSettings, setArchiveSettings] = useState<ArchiveSettings | null>(null);
  const [archiveSettingsLoading, setArchiveSettingsLoading] = useState(true);
  const [archiveEnabled, setArchiveEnabled] = useState(false);
  const [archiveIncludePdfs, setArchiveIncludePdfs] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  const [exportHistory, setExportHistory] = useState<ExportLog[]>([]);
  const [exportHistoryLoading, setExportHistoryLoading] = useState(true);

  const [showPeriodPicker, setShowPeriodPicker] = useState(false);
  const [triggeringExport, setTriggeringExport] = useState(false);
  const [archiveToast, setArchiveToast] = useState<{ message: string; ok: boolean } | null>(null);

  // ── Audit export section state ──────────────────────────────────
  const [dateFrom, setDateFrom] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-01-01`;
  });
  const [dateTo, setDateTo] = useState(() => {
    return new Date().toISOString().slice(0, 10);
  });
  const [includeDocuments, setIncludeDocuments] = useState(true);
  const [includeAuditTrail, setIncludeAuditTrail] = useState(true);
  const [includeVatSummary, setIncludeVatSummary] = useState(true);
  const [reason, setReason] = useState('');
  const [generating, setGenerating] = useState(false);
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<string | null>(null);
  const [auditHistory, setAuditHistory] = useState<AuditExportResponse[]>([]);
  const [auditHistoryLoading, setAuditHistoryLoading] = useState(true);
  const [auditHistoryError, setAuditHistoryError] = useState('');
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);

  // ── Load archive settings & history ────────────────────────────
  const loadArchiveData = useCallback(async () => {
    setArchiveSettingsLoading(true);
    setExportHistoryLoading(true);
    try {
      const [settings, history] = await Promise.all([
        fetchArchiveSettings().catch(() => null),
        fetchExportHistory().catch(() => [] as ExportLog[]),
      ]);
      if (settings) {
        setArchiveSettings(settings);
        setArchiveEnabled(settings.enabled);
        setArchiveIncludePdfs(settings.include_pdfs);
      }
      setExportHistory(Array.isArray(history) ? history : []);
    } finally {
      setArchiveSettingsLoading(false);
      setExportHistoryLoading(false);
    }
  }, []);

  // ── Load audit export history ───────────────────────────────────
  const loadAuditHistory = useCallback(async () => {
    setAuditHistoryLoading(true);
    setAuditHistoryError('');
    try {
      const data = await fetchAuditExportHistory();
      setAuditHistory(data);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setAuditHistoryError(tAudit('errorHistory'));
      }
    } finally {
      setAuditHistoryLoading(false);
    }
  }, [tAudit]);

  useEffect(() => {
    if (isAdmin) {
      loadArchiveData();
      loadAuditHistory();
    }
  }, [isAdmin, loadArchiveData, loadAuditHistory]);

  // ── Preview count for audit form ────────────────────────────────
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

  // ── Admin guard ─────────────────────────────────────────────────
  if (!isAdmin) return <AccessDenied />;
  if (planError) return <UpgradeModal error={planError} onClose={() => window.history.back()} />;

  // ── Archive settings save ───────────────────────────────────────
  async function handleSaveSettings(enabled: boolean, includePdfs: boolean) {
    setSavingSettings(true);
    try {
      const updated = await updateArchiveSettings(enabled, includePdfs);
      setArchiveSettings(updated);
      setArchiveEnabled(updated.enabled);
      setArchiveIncludePdfs(updated.include_pdfs);
    } catch {
      // revert on error
      if (archiveSettings) {
        setArchiveEnabled(archiveSettings.enabled);
        setArchiveIncludePdfs(archiveSettings.include_pdfs);
      }
    } finally {
      setSavingSettings(false);
    }
  }

  function handleToggleEnabled(val: boolean) {
    setArchiveEnabled(val);
    handleSaveSettings(val, archiveIncludePdfs);
  }

  function handleToggleIncludePdfs(val: boolean) {
    setArchiveIncludePdfs(val);
    handleSaveSettings(archiveEnabled, val);
  }

  async function handleTriggerExport(period: string) {
    setTriggeringExport(true);
    try {
      await triggerArchiveExport(period);
      setShowPeriodPicker(false);
      setArchiveToast({ message: tArchive('exportSuccess'), ok: true });
      setTimeout(() => setArchiveToast(null), 4000);
      await loadArchiveData();
    } catch {
      setArchiveToast({ message: tArchive('exportFailed'), ok: false });
      setTimeout(() => setArchiveToast(null), 4000);
    } finally {
      setTriggeringExport(false);
    }
  }

  // ── Audit form handlers ─────────────────────────────────────────
  function validate(): boolean {
    setError('');
    if (!dateFrom || !dateTo) { setError(tAudit('errorDateRequired')); return false; }
    if (dateFrom > dateTo) { setError(tAudit('errorDateRange')); return false; }
    return true;
  }

  async function handleGenerate() {
    if (!validate()) return;
    setGenerating(true);
    setError('');
    try {
      await createAuditExport({
        date_from: dateFrom,
        date_to: dateTo,
        include_documents: includeDocuments,
        include_audit_trail: includeAuditTrail,
        include_vat_summary: includeVatSummary,
        reason: reason.trim() || undefined,
      });
      setToast(tAudit('successGenerate'));
      setTimeout(() => setToast(null), 4000);
      setReason('');
      await loadAuditHistory();
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setError(tAudit('errorGenerate'));
      }
    } finally {
      setGenerating(false);
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────
  function formatBytes(bytes: number | null): string {
    if (bytes == null) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">{tArchive('title')}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{tArchive('subtitle')}</p>
      </div>

      {/* ── Section 1: Automatski mesečni izvoz ────────────────────── */}
      <div className="mb-6">
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          {/* Section header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">{tArchive('monthlyExportTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{tArchive('monthlyExportDesc')}</p>
            </div>
            {savingSettings && (
              <svg className="w-4 h-4 animate-spin text-violet-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
          </div>

          {archiveSettingsLoading ? (
            <div className="flex items-center justify-center py-6">
              <svg className="w-5 h-5 animate-spin text-violet-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          ) : (
            <div className="space-y-0">
              {/* Enable toggle */}
              <div className="border-b border-gray-100 pb-2 mb-2">
                <ContentToggle
                  checked={archiveEnabled}
                  onChange={handleToggleEnabled}
                  disabled={savingSettings}
                  title={tArchive('enabled')}
                  description=""
                />
              </div>

              {/* Include PDFs checkbox */}
              <ContentToggle
                checked={archiveIncludePdfs}
                onChange={handleToggleIncludePdfs}
                disabled={savingSettings || !archiveEnabled}
                title={tArchive('includePdfs')}
                description=""
              />

              {/* Delivery email */}
              <div className="pt-3 pb-1">
                <p className="text-xs font-medium text-gray-500 mb-1">{tArchive('deliveryEmail')}</p>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-gray-900 font-medium truncate">
                    {archiveSettings?.email || '—'}
                  </span>
                  <span className="text-xs text-gray-400 shrink-0">{tArchive('changeEmail')}</span>
                </div>
              </div>

              {/* Test button */}
              <div className="pt-3 border-t border-gray-100 mt-3 flex justify-end">
                <button
                  onClick={() => setShowPeriodPicker(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-lg transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {tArchive('testNow')}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Delivery history table */}
        <div className="mt-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
            {tArchive('deliveryHistory')}
          </h3>

          {exportHistoryLoading ? (
            <div className="flex items-center justify-center py-6">
              <svg className="w-5 h-5 animate-spin text-violet-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          ) : exportHistory.length === 0 ? (
            <div className="text-center py-6 bg-white border border-gray-200 rounded-xl">
              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-2">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M8 4H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-2m-4-1v8m0 0l-3-3m3 3l3-3" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">{tArchive('noHistory')}</p>
            </div>
          ) : (
            <>
              {/* Desktop table */}
              <div className="hidden sm:block bg-white border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50/50">
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('period')}</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('status')}</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('deliveredTo')}</th>
                      <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('invoiceCount')}</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('fileSize')}</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tArchive('deliveredAt')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exportHistory.map((item) => {
                      const statusLabel = (tArchive as (k: string) => string)(
                        item.status === 'delivered' ? 'delivered'
                          : item.status === 'failed' ? 'failed'
                          : 'skipped'
                      );
                      return (
                        <tr key={item.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50">
                          <td className="px-3 py-2.5 text-sm font-medium text-gray-900">{item.period}</td>
                          <td className="px-3 py-2.5">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${ARCHIVE_STATUS_STYLES[item.status] || ARCHIVE_STATUS_STYLES.skipped}`}>
                              {statusLabel}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-sm text-gray-600 max-w-[160px] truncate">{item.delivered_to || '—'}</td>
                          <td className="px-3 py-2.5 text-sm text-gray-600 text-center">{item.invoice_count ?? '—'}</td>
                          <td className="px-3 py-2.5 text-sm text-gray-600">{formatBytes(item.file_size_bytes)}</td>
                          <td className="px-3 py-2.5 text-sm text-gray-500">{item.delivered_at ? formatRelativeTime(item.delivered_at) : '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="sm:hidden space-y-2">
                {exportHistory.map((item) => {
                  const statusLabel = (tArchive as (k: string) => string)(
                    item.status === 'delivered' ? 'delivered'
                      : item.status === 'failed' ? 'failed'
                      : 'skipped'
                  );
                  return (
                    <div key={item.id} className="bg-white border border-gray-200 rounded-xl p-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">{item.period}</span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${ARCHIVE_STATUS_STYLES[item.status] || ARCHIVE_STATUS_STYLES.skipped}`}>
                          {statusLabel}
                        </span>
                      </div>
                      <div className="flex gap-3 text-xs text-gray-500 flex-wrap">
                        <span>{item.delivered_to || '—'}</span>
                        <span>{item.invoice_count ?? '—'} faktura</span>
                        <span>{formatBytes(item.file_size_bytes)}</span>
                      </div>
                      {item.delivered_at && (
                        <p className="text-xs text-gray-400">{formatRelativeTime(item.delivered_at)}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Visual separator ───────────────────────────────────────── */}
      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center">
          <span className="px-3 bg-gray-50 text-xs font-medium text-gray-400 uppercase tracking-wider">
            {tArchive('taxExportTitle')}
          </span>
        </div>
      </div>

      {/* ── Section 2: Izvoz za poresku inspekciju ─────────────────── */}

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
        <div className="lg:col-span-3 bg-white border border-gray-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">{tAudit('sectionGenerate')}</h2>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label htmlFor="dateFrom" className="block text-xs font-medium text-gray-600 mb-1">
                {tAudit('dateFrom')}
              </label>
              <input
                id="dateFrom"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-500"
              />
            </div>
            <div>
              <label htmlFor="dateTo" className="block text-xs font-medium text-gray-600 mb-1">
                {tAudit('dateTo')}
              </label>
              <input
                id="dateTo"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-500"
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

          {/* Content toggles */}
          <div className="border-t border-gray-100 pt-2 mb-3">
            <ContentToggle
              checked={true}
              disabled={true}
              title={tAudit('includeRegister')}
              description={tAudit('includeRegisterDesc')}
              badge={tAudit('includeRegisterAlways')}
            />
            <ContentToggle
              checked={includeVatSummary}
              onChange={setIncludeVatSummary}
              title={tAudit('includeVatSummary')}
              description={tAudit('includeVatSummaryDesc')}
            />
            <ContentToggle
              checked={includeAuditTrail}
              onChange={setIncludeAuditTrail}
              title={tAudit('includeAuditTrail')}
              description={tAudit('includeAuditTrailDesc')}
            />
            <ContentToggle
              checked={includeDocuments}
              onChange={setIncludeDocuments}
              title={tAudit('includeDocuments')}
              description={tAudit('includeDocumentsDesc')}
            />
          </div>

          {/* Reason + Generate */}
          <div className="flex gap-3 items-end">
            <div className="flex-1">
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
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="shrink-0 inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating && (
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {generating ? tAudit('generating') : tAudit('generate')}
            </button>
          </div>
        </div>

        {/* Right: Info panel (2/5) */}
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

      {/* Audit history section — full width */}
      <div>
        <h2 className="text-sm font-semibold text-gray-900 mb-2">{tAudit('sectionHistory')}</h2>

        {auditHistoryLoading ? (
          <div className="flex items-center justify-center py-8">
            <svg className="w-5 h-5 animate-spin text-violet-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        ) : auditHistoryError ? (
          <div className="text-center py-8">
            <p className="text-sm text-red-500">{auditHistoryError}</p>
            <button
              onClick={loadAuditHistory}
              className="mt-1 text-sm text-violet-600 hover:text-violet-700 underline"
            >
              Pokušaj ponovo
            </button>
          </div>
        ) : auditHistory.length === 0 ? (
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
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnReason')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{tAudit('columnActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {auditHistory.map((item) => (
                    <AuditHistoryRow key={item.id} item={item} t={tAudit} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="sm:hidden space-y-2">
              {auditHistory.map((item) => (
                <AuditHistoryCard key={item.id} item={item} t={tAudit} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Period picker modal */}
      {showPeriodPicker && (
        <PeriodPickerModal
          onConfirm={handleTriggerExport}
          onClose={() => setShowPeriodPicker(false)}
          generating={triggeringExport}
          tArchive={tArchive}
        />
      )}

      {/* Archive toast */}
      {archiveToast && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl shadow-lg ${archiveToast.ok ? 'bg-gray-900 text-white' : 'bg-red-600 text-white'}`}>
          {archiveToast.ok ? (
            <svg className="w-4 h-4 text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-red-200 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          {archiveToast.message}
        </div>
      )}

      {/* Audit export toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white text-sm rounded-xl shadow-lg">
          <svg className="w-4 h-4 text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {toast}
        </div>
      )}

      {/* Upgrade modal */}
      {planError && (
        <UpgradeModal error={planError} onClose={() => setPlanError(null)} />
      )}
    </div>
  );
}
