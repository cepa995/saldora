'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { exportInvoices, pushToMinimax, triggerBrowserDownload } from '@/lib/api/export';
import { Toast, type ToastType } from '@/components/Toast';
import type { ExportFormat, ExportOptions, BlockedInvoice, MiniMaxPushResult } from '@/lib/types/export';

interface ExportDialogProps {
  invoiceIds: string[];
  onClose: () => void;
  onSuccess?: () => void;
}

const FORMATS: { key: ExportFormat; labelKey: string; descKey: string }[] = [
  { key: 'xlsx', labelKey: 'formatXlsx', descKey: 'formatXlsxDesc' },
  { key: 'csv', labelKey: 'formatCsv', descKey: 'formatCsvDesc' },
  { key: 'json', labelKey: 'formatJson', descKey: 'formatJsonDesc' },
  { key: 'minimax_xml', labelKey: 'formatMinimax_xml', descKey: 'formatMinimax_xmlDesc' },
];

/**
 * Modal dialog for exporting invoices in various formats.
 *
 * Displays format selection cards, format-specific options, and handles
 * the download flow including error/blocked invoice display.
 * For MiniMax XML, also supports direct push to MiniMax API.
 */
export function ExportDialog({ invoiceIds, onClose, onSuccess }: ExportDialogProps) {
  const t = useTranslations('export');
  const tCommon = useTranslations('common');
  const dialogRef = useRef<HTMLDivElement>(null);

  const [format, setFormat] = useState<ExportFormat>('xlsx');
  const [options, setOptions] = useState<ExportOptions>({
    include_line_items: true,
    nested_json: false,
    decimal_separator: ',',
    delimiter: 'semicolon',
  });
  const [isExporting, setIsExporting] = useState(false);
  const [isPushing, setIsPushing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blockedInvoices, setBlockedInvoices] = useState<BlockedInvoice[] | null>(null);
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);
  const [createCustomers, setCreateCustomers] = useState(true);
  const [pushResults, setPushResults] = useState<MiniMaxPushResult[] | null>(null);

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Close on backdrop click
  function handleBackdropClick(e: React.MouseEvent) {
    if (dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
      onClose();
    }
  }

  // Clear errors and results when format changes
  function handleFormatChange(newFormat: ExportFormat) {
    setFormat(newFormat);
    setError(null);
    setBlockedInvoices(null);
    setPushResults(null);
  }

  async function handleExport() {
    setIsExporting(true);
    setError(null);
    setBlockedInvoices(null);

    try {
      const { blob, filename } = await exportInvoices(format, invoiceIds, options);
      triggerBrowserDownload(blob, filename);
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      const apiErr = err as Record<string, unknown>;
      if (apiErr.status === 422 && Array.isArray(apiErr.blockedInvoices)) {
        setBlockedInvoices(apiErr.blockedInvoices as BlockedInvoice[]);
        setToast({ message: t('blockedToast'), type: 'error' });
      } else {
        setError((apiErr.message as string) || t('exportError'));
      }
    } finally {
      setIsExporting(false);
    }
  }

  async function handlePushToMinimax() {
    setIsPushing(true);
    setError(null);
    setPushResults(null);

    try {
      const response = await pushToMinimax(invoiceIds, createCustomers);
      setPushResults(response.results);
      if (response.error_count === 0) {
        setToast({ message: t('pushSuccess', { count: response.success_count.toString() }), type: 'success' });
        onSuccess?.();
      } else if (response.success_count > 0) {
        setToast({
          message: t('pushPartial', {
            success: response.success_count.toString(),
            errors: response.error_count.toString(),
          }),
          type: 'error',
        });
      } else {
        setToast({ message: t('pushFailed'), type: 'error' });
      }
    } catch (err: unknown) {
      const apiErr = err as Record<string, unknown>;
      setError((apiErr.message as string) || t('pushError'));
    } finally {
      setIsPushing(false);
    }
  }

  const isBusy = isExporting || isPushing;

  function renderFormatIcon(fmt: ExportFormat) {
    switch (fmt) {
      case 'xlsx':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M3 14h18M9 4v16M15 4v16M4 4h16a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V5a1 1 0 011-1z" />
          </svg>
        );
      case 'csv':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case 'json':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        );
      case 'minimax_xml':
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        );
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{t('dialogTitle')}</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {t('invoiceCount', { count: invoiceIds.length.toString() })}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Format selection */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {FORMATS.map(({ key, labelKey, descKey }) => (
            <button
              key={key}
              onClick={() => handleFormatChange(key)}
              className={`flex items-center gap-3 p-3 rounded-xl border-2 text-left transition-all ${
                format === key
                  ? 'border-violet-600 bg-violet-50 ring-1 ring-violet-600'
                  : 'border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300'
              }`}
            >
              <div className={`${format === key ? 'text-violet-600' : 'text-gray-500'}`}>
                {renderFormatIcon(key)}
              </div>
              <div>
                <div className={`text-sm font-medium ${format === key ? 'text-violet-900' : 'text-gray-900'}`}>
                  {t(labelKey as 'formatXlsx')}
                </div>
                <div className="text-xs text-gray-500">
                  {t(descKey as 'formatXlsxDesc')}
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Format-specific options */}
        <div className="space-y-3 mb-6">
          <h3 className="text-sm font-medium text-gray-700">{t('options')}</h3>

          {/* XLSX: include line items */}
          {format === 'xlsx' && (
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={options.include_line_items ?? true}
                onChange={(e) => setOptions({ ...options, include_line_items: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
              />
              <span className="text-sm text-gray-700">{t('includeLineItems')}</span>
            </label>
          )}

          {/* CSV: include line items + delimiter */}
          {format === 'csv' && (
            <>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.include_line_items ?? true}
                  onChange={(e) => setOptions({ ...options, include_line_items: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                />
                <span className="text-sm text-gray-700">{t('includeLineItems')}</span>
              </label>
              <div>
                <label className="block text-sm text-gray-600 mb-1">{t('delimiter')}</label>
                <select
                  value={options.delimiter ?? 'semicolon'}
                  onChange={(e) => setOptions({ ...options, delimiter: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                >
                  <option value="semicolon">{t('delimiterSemicolon')}</option>
                  <option value="comma">{t('delimiterComma')}</option>
                  <option value="tab">{t('delimiterTab')}</option>
                </select>
              </div>
            </>
          )}

          {/* JSON: nested toggle */}
          {format === 'json' && (
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={options.nested_json ?? false}
                onChange={(e) => setOptions({ ...options, nested_json: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
              />
              <span className="text-sm text-gray-700">{t('nestedJson')}</span>
            </label>
          )}

          {/* MiniMax XML: push options */}
          {format === 'minimax_xml' && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 italic">{t('formatMinimaxDesc')}</p>
              <div className="p-3 bg-violet-50 border border-violet-100 rounded-xl space-y-2">
                <p className="text-xs font-medium text-violet-800">{t('pushToMinimaxTitle')}</p>
                <p className="text-xs text-violet-600">{t('pushToMinimaxDesc')}</p>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={createCustomers}
                    onChange={(e) => setCreateCustomers(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                  />
                  <span className="text-xs text-violet-700">{t('createCustomers')}</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Blocked invoices display */}
        {blockedInvoices && (
          <div className="mb-4 p-4 bg-red-50 border border-red-100 rounded-xl space-y-2">
            <p className="text-sm font-medium text-red-700">{t('blockedTitle')}</p>
            {blockedInvoices.map((inv) => (
              <div key={inv.invoice_id} className="text-sm text-red-600">
                <span className="font-mono text-xs">{inv.invoice_number || inv.invoice_id.slice(0, 8)}</span>
                <ul className="ml-4 list-disc">
                  {inv.reasons.map((reason, i) => (
                    <li key={i} className="text-xs">{reason}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {/* MiniMax push results */}
        {pushResults && (
          <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-2">
            <p className="text-sm font-medium text-gray-700">{t('pushResults')}</p>
            {pushResults.map((result) => (
              <div key={result.invoice_id} className="flex items-center gap-2 text-sm">
                {result.status === 'success' ? (
                  <svg className="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                <span className="font-mono text-xs text-gray-600">
                  {result.invoice_number || result.invoice_id.slice(0, 8)}
                </span>
                {result.status === 'success' ? (
                  <span className="text-xs text-green-600">
                    MiniMax ID: {result.minimax_id}
                  </span>
                ) : (
                  <span className="text-xs text-red-600">{result.error}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
          <button
            onClick={onClose}
            disabled={isBusy}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-xl transition-colors disabled:opacity-50"
          >
            {tCommon('cancel')}
          </button>

          {/* MiniMax push button (only for minimax_xml format) */}
          {format === 'minimax_xml' && (
            <button
              onClick={handlePushToMinimax}
              disabled={isBusy}
              className="px-4 py-2 text-sm font-medium text-violet-700 bg-violet-100 hover:bg-violet-200 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isPushing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t('pushing')}
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  {t('pushToMinimax')}
                </>
              )}
            </button>
          )}

          <button
            onClick={handleExport}
            disabled={isBusy}
            className="px-5 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isExporting ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {t('exporting')}
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {t('download')}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Toast notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
