'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { fetchClientObligations } from '@/lib/api/clients';
import type {
  ClientObligationsResponse,
  ObligationFormKey,
  ObligationFormStatus,
} from '@/lib/types/client';

interface Props {
  clientId: string;
  orgSlug: string;
}

const FORM_ORDER: ObligationFormKey[] = [
  'kalkulacija',
  'kep',
  'cenovnik',
  'popis',
  'dpu',
  'pk1',
];

/** Map a form key to the report tab id, if any. Used to deep-link from
 * the popover to the existing report via ?tab=izvestaji&report=<id>. */
const FORM_TO_REPORT_TAB: Partial<Record<ObligationFormKey, string>> = {
  kalkulacija: 'kalkulacija',
  dpu: 'dpu',
};

/**
 * "Obavezni obrasci" trigger + popover. Lives in the client workspace
 * header next to the legal-form / bookkeeping meta chips — the obligation
 * matrix is the consequence of those two classifications, so colocating
 * keeps cause-and-effect together and frees the Izveštaji tab.
 *
 * Backend remains the single source of truth
 * (`app.services.hospitality_forms.required_forms`).
 */
export function ObligationsPopover({ clientId, orgSlug }: Props) {
  const t = useTranslations('obligations');
  const tClients = useTranslations('clients');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const [data, setData] = useState<ClientObligationsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchClientObligations(clientId);
      setData(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  // Close on outside click and Escape.
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    window.addEventListener('mousedown', onClick);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('mousedown', onClick);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const visibleForms = useMemo(
    () =>
      FORM_ORDER.filter(
        (key) => (data?.forms[key] ?? 'unclassified') !== 'not_applicable',
      ),
    [data],
  );
  const summary = useMemo(() => {
    let owed = 0;
    let ready = 0;
    let postMeeting = 0;
    if (!data) return { owed, ready, postMeeting };
    for (const key of FORM_ORDER) {
      const s = data.forms[key];
      if (s === 'not_applicable') continue;
      owed += 1;
      if (s === 'shipped' || s === 'pre_meeting') ready += 1;
      else if (s === 'post_meeting') postMeeting += 1;
    }
    return { owed, ready, postMeeting };
  }, [data]);

  const allUnclassified =
    data !== null && FORM_ORDER.every((key) => data.forms[key] === 'unclassified');

  // Trigger label: classified clients show "ready/owed", unclassified
  // shows a subtle prompt so the agency knows there's something to set.
  const triggerCount = allUnclassified
    ? '?'
    : `${summary.ready}/${summary.owed}`;

  function handleJumpToReport(key: ObligationFormKey) {
    const reportId = FORM_TO_REPORT_TAB[key];
    if (!reportId) return;
    setOpen(false);
    router.push(
      `/${orgSlug}/klijenti/${clientId}?tab=izvestaji&report=${reportId}`,
    );
  }

  // Classification subtitle inside the popover.
  const classificationParts: string[] = [];
  if (data?.legal_form) {
    classificationParts.push(tClients(`legalFormOption.${data.legal_form}`));
  }
  if (data?.bookkeeping_system) {
    classificationParts.push(
      tClients(`bookkeepingOption.${data.bookkeeping_system}`),
    );
  } else if (data?.legal_form === 'DOO') {
    classificationParts.push(`${tClients('bookkeepingOption.dvojno')} *`);
  }
  const classification = classificationParts.join(' · ');

  return (
    <div className="relative inline-block" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        aria-expanded={open}
        aria-haspopup="dialog"
        disabled={isLoading || !!error}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-50 text-[11px] font-medium text-violet-700 ring-1 ring-violet-200/70 hover:bg-violet-100 transition-colors disabled:opacity-60 disabled:cursor-default"
      >
        <svg
          className="w-3 h-3 text-violet-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <span className="text-violet-800">{t('title')}</span>
        {!isLoading && !error && (
          <span className="text-violet-500 tabular-nums">{triggerCount}</span>
        )}
      </button>

      {open && data && (
        <div
          role="dialog"
          aria-label={t('title')}
          className="absolute left-0 sm:right-0 sm:left-auto mt-2 w-[min(22rem,calc(100vw-2rem))] sm:w-96 z-30 rounded-2xl border border-stone-200 bg-white shadow-lg shadow-stone-900/10 overflow-hidden"
        >
          <div className="px-4 py-3 border-b border-stone-100">
            <p className="text-sm font-semibold text-stone-900">{t('title')}</p>
            {!allUnclassified && (
              <p className="text-[11px] text-stone-500 mt-0.5">
                {t('summaryLine', {
                  owed: summary.owed,
                  ready: summary.ready,
                  postMeeting: summary.postMeeting,
                })}
              </p>
            )}
            {classification && (
              <p className="text-[11px] text-stone-500 mt-0.5">{classification}</p>
            )}
          </div>

          {allUnclassified ? (
            <p className="px-4 py-3 text-sm text-amber-800 bg-amber-50/70">
              {t('unclassifiedPrompt')}
            </p>
          ) : (
            <>
              <ul className="divide-y divide-stone-100 max-h-[24rem] overflow-y-auto">
                {visibleForms.map((key) => {
                  const status = data.forms[key];
                  const reportTab = FORM_TO_REPORT_TAB[key];
                  const isShipped =
                    status === 'shipped' || status === 'pre_meeting';
                  const canOpen = isShipped && reportTab;
                  return (
                    <li
                      key={key}
                      className="px-4 py-2 flex items-center justify-between gap-3"
                    >
                      <p className="text-[13px] font-medium text-stone-900 truncate">
                        {t(`form.${key}.name`)}
                      </p>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <StatusPill status={status} />
                        {canOpen && (
                          <button
                            type="button"
                            onClick={() => handleJumpToReport(key)}
                            className="px-2 py-1 text-[11px] font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-md transition-colors"
                          >
                            {t('open')}
                          </button>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
              {data.legal_form === 'DOO' && !data.bookkeeping_system && (
                <p className="px-4 py-2 text-[10px] text-stone-500 italic border-t border-stone-100">
                  * {tClients('dooImpliesDvojno')}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {open && error && (
        <div
          role="alert"
          className="absolute left-0 sm:right-0 sm:left-auto mt-2 w-72 z-30 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          {error}
        </div>
      )}
    </div>
  );
}

const STATUS_CLASSES: Record<ObligationFormStatus, string> = {
  shipped: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  pre_meeting: 'bg-violet-50 text-violet-700 ring-violet-200',
  post_meeting: 'bg-amber-50 text-amber-700 ring-amber-200',
  not_applicable: 'bg-stone-50 text-stone-500 ring-stone-200',
  unclassified: 'bg-amber-50 text-amber-700 ring-amber-200',
};

function StatusPill({ status }: { status: ObligationFormStatus }) {
  const t = useTranslations('obligations.status');
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset whitespace-nowrap ${STATUS_CLASSES[status]}`}
    >
      {t(status)}
    </span>
  );
}
