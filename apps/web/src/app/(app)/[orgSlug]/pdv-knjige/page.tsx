'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useClient } from '@/contexts/ClientContext';
import { isPlanError } from '@/lib/api-client';
import { UpgradeModal, type PlanErrorInfo } from '@/components/UpgradeModal';
import { previewPdvBook, generatePdvBook } from '@/lib/api/pdv-books';

export default function PdvKnjigePage() {
  const t = useTranslations('pdvBooks');
  const { user } = useAuth();
  const { clients, isAgency } = useClient();

  const now = new Date();
  const [bookType, setBookType] = useState<'KPR' | 'KIR'>('KPR');
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [format, setFormat] = useState<'xlsx' | 'csv'>('xlsx');
  const [clientId, setClientId] = useState<string>('');

  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);

  const period = `${year}-${String(month).padStart(2, '0')}`;

  // Fetch preview count when parameters change
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const result = await previewPdvBook(bookType, period, clientId || undefined);
        if (!cancelled) setPreviewCount(result.entry_count);
      } catch (err) {
        if (!cancelled) {
          if (isPlanError(err)) {
            setPlanError(err.planError as PlanErrorInfo);
          }
          setPreviewCount(null);
        }
      }
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [bookType, period, clientId]);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    try {
      const { blob, filename } = await generatePdvBook(
        bookType,
        period,
        format,
        clientId || undefined,
      );
      // Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setToast({ message: t('downloadReady'), type: 'success' });
      setTimeout(() => setToast(null), 4000);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setToast({ message: t('error'), type: 'error' });
        setTimeout(() => setToast(null), 4000);
      }
    } finally {
      setGenerating(false);
    }
  }, [bookType, period, format, clientId, t]);

  // Plan gate
  if (planError) {
    return <UpgradeModal error={planError} onClose={() => window.history.back()} />;
  }

  const currentYear = now.getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  return (
    <div>
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{t('description')}</p>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`mb-3 p-2.5 rounded-lg border text-sm flex items-center justify-between ${
          toast.type === 'success'
            ? 'bg-green-50 border-green-200 text-green-700'
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-3 shrink-0 opacity-60 hover:opacity-100">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Form card */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        {/* Book type selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">{t('bookType')}</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setBookType('KPR')}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                bookType === 'KPR'
                  ? 'bg-violet-50 border-violet-300 text-violet-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span className="sm:hidden">{t('kprShort')}</span>
              <span className="hidden sm:inline">{t('kpr')}</span>
            </button>
            <button
              type="button"
              onClick={() => setBookType('KIR')}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                bookType === 'KIR'
                  ? 'bg-violet-50 border-violet-300 text-violet-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span className="sm:hidden">{t('kirShort')}</span>
              <span className="hidden sm:inline">{t('kir')}</span>
            </button>
          </div>
        </div>

        {/* Period selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">{t('period')}</label>
          <div className="flex gap-2">
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            >
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>
                  {t(`months.${i + 1}`)}
                </option>
              ))}
            </select>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-28 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            >
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Client selector (agency only) */}
        {isAgency && clients.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">{t('client')}</label>
            <select
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            >
              <option value="">{t('allClients')}</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.pib})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Format selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">{t('format')}</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setFormat('xlsx')}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                format === 'xlsx'
                  ? 'bg-violet-50 border-violet-300 text-violet-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              XLSX
            </button>
            <button
              type="button"
              onClick={() => setFormat('csv')}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                format === 'csv'
                  ? 'bg-violet-50 border-violet-300 text-violet-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              CSV
            </button>
          </div>
        </div>

        {/* Preview count */}
        {previewCount !== null && (
          <div className={`text-sm px-3 py-2 rounded-lg ${
            previewCount > 0
              ? 'bg-blue-50 text-blue-700'
              : 'bg-gray-50 text-gray-500'
          }`}>
            {previewCount > 0
              ? t('entryCount', { count: String(previewCount) })
              : t('noEntries')
            }
          </div>
        )}

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={generating || previewCount === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 text-white text-sm font-medium rounded-xl transition-colors"
        >
          {generating ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {t('generating')}
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              {t('generate')}
            </>
          )}
        </button>
      </div>

      {/* Tips & Tricks */}
      <div className="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2.5">
          <svg className="w-4 h-4 text-amber-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h3 className="text-sm font-semibold text-amber-900">{t('tipsTitle')}</h3>
        </div>
        <ul className="space-y-2">
          <li className="text-xs text-amber-700 flex gap-2">
            <span className="text-amber-500 shrink-0 mt-0.5">1.</span>
            <span>{t('tipVerify')}</span>
          </li>
          <li className="text-xs text-amber-700 flex gap-2">
            <span className="text-amber-500 shrink-0 mt-0.5">2.</span>
            <span>{t('tipPpPdv')}</span>
          </li>
          <li className="text-xs text-amber-700 flex gap-2">
            <span className="text-amber-500 shrink-0 mt-0.5">3.</span>
            <span>{t('tipXlsx')}</span>
          </li>
          <li className="text-xs text-amber-700 flex gap-2">
            <span className="text-amber-500 shrink-0 mt-0.5">4.</span>
            <span>{t('tipKprKir')}</span>
          </li>
          <li className="text-xs text-amber-700 flex gap-2">
            <span className="text-amber-500 shrink-0 mt-0.5">5.</span>
            <span>{t('tipMonthly')}</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
