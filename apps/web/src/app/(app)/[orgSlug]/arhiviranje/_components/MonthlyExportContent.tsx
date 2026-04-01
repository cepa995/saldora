'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  fetchExportHistory,
  fetchArchiveSettings,
  updateArchiveSettings,
  triggerArchiveExport,
  type ExportLog,
  type ArchiveSettings,
} from '@/lib/api/archive';
import { formatRelativeTime } from '@/lib/formatters';

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

// ── Helpers ─────────────────────────────────────────────────────────

function formatBytes(bytes: number | null): string {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── MonthlyExportContent ────────────────────────────────────────────

export default function MonthlyExportContent() {
  const tArchive = useTranslations('archive');

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

  useEffect(() => {
    loadArchiveData();
  }, [loadArchiveData]);

  async function handleSaveSettings(enabled: boolean, includePdfs: boolean) {
    setSavingSettings(true);
    try {
      const updated = await updateArchiveSettings(enabled, includePdfs);
      setArchiveSettings(updated);
      setArchiveEnabled(updated.enabled);
      setArchiveIncludePdfs(updated.include_pdfs);
    } catch {
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

  return (
    <div>
      {/* Settings card */}
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
    </div>
  );
}
