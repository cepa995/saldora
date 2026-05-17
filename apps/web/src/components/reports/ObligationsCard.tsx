'use client';

/**
 * "Obavezni obrasci" card — shown at the top of the per-client Izveštaji
 * tab. Renders the obligation matrix returned by
 * `GET /api/v1/clients/{id}/obligations`. Frontend never re-derives;
 * the backend is the single source of truth (see
 * `app.services.hospitality_forms.required_forms`).
 *
 * For the M20 accountant meeting, this is *the* surface the accountant
 * pushes back on. Each row shows the form, the per-client status, and
 * (when available) a link to open the corresponding existing report.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { fetchClientObligations } from '@/lib/api/clients';
import type {
  ClientObligationsResponse,
  ObligationFormKey,
  ObligationFormStatus,
} from '@/lib/types/client';

interface Props {
  clientId: string;
  /** Called when the user picks a form whose status is "shipped"; the
   * parent (ReportsSurface) selects the matching report tab. */
  onJumpToReport?: (key: ObligationFormKey) => void;
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
 * the obligation card to the existing report. */
const FORM_TO_REPORT_TAB: Partial<Record<ObligationFormKey, string>> = {
  kalkulacija: 'kalkulacija',
  dpu: 'dpu',
};

export function ObligationsCard({ clientId, onJumpToReport }: Props) {
  const t = useTranslations('obligations');
  const tClients = useTranslations('clients');
  const tCommon = useTranslations('common');

  const [data, setData] = useState<ClientObligationsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // Default-collapsed. The card is the M20 demo hero but daily users
  // don't need it dominating the viewport — they expand on demand.
  const [expanded, setExpanded] = useState(false);

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

  // Hooks must run unconditionally; compute these even when `data` is null
  // (the early returns below skip rendering, not hook execution).
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

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        {error}
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="rounded-2xl border border-stone-200 bg-white p-5 animate-pulse">
        <div className="h-4 w-48 bg-stone-100 rounded mb-3" />
        <div className="space-y-2">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-5 w-full bg-stone-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  // Build the classification subtitle from whatever the agency has set.
  const classificationParts: string[] = [];
  if (data.legal_form) {
    classificationParts.push(tClients(`legalFormOption.${data.legal_form}`));
  }
  if (data.bookkeeping_system) {
    classificationParts.push(
      tClients(`bookkeepingOption.${data.bookkeeping_system}`),
    );
  } else if (data.legal_form === 'DOO') {
    // DOO is implied to be dvojno by Zakon o računovodstvu; we show the
    // implied value so the accountant sees what the matrix used.
    classificationParts.push(`${tClients('bookkeepingOption.dvojno')} *`);
  }
  const classification = classificationParts.join(' · ');

  // If nothing is classified yet, show a friendly prompt rather than a
  // table full of "unclassified" pills.
  const allUnclassified = FORM_ORDER.every(
    (key) => data.forms[key] === 'unclassified',
  );
  if (allUnclassified) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-5">
        <h3 className="text-sm font-semibold text-amber-900">{t('title')}</h3>
        <p className="text-sm text-amber-800 mt-1">{t('unclassifiedPrompt')}</p>
      </div>
    );
  }

  // visibleForms + summary are computed unconditionally above so the
  // hooks fire in a consistent order across renders. We just consume
  // them here.

  return (
    <div className="rounded-2xl border border-stone-200 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.02)] overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
        className="w-full text-left px-5 py-3 flex items-center justify-between gap-3 hover:bg-stone-50 transition-colors"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <svg
            className={`w-3.5 h-3.5 text-stone-400 shrink-0 transition-transform ${
              expanded ? 'rotate-90' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-sm font-semibold text-stone-900 truncate">
            {t('title')}
          </span>
          <span className="text-[11px] text-stone-500 truncate">
            {t('summaryLine', {
              owed: summary.owed,
              ready: summary.ready,
              postMeeting: summary.postMeeting,
            })}
          </span>
        </div>
        {classification && (
          <span className="text-[11px] text-stone-500 shrink-0">{classification}</span>
        )}
      </button>

      {expanded && (
        <>
          <p className="px-5 pt-1 pb-2 text-[11px] text-stone-500 border-t border-stone-100">
            {t('subtitle')}
          </p>
          <ul className="divide-y divide-stone-100">
            {visibleForms.map((key) => {
              const status = data.forms[key];
              const reportTab = FORM_TO_REPORT_TAB[key];
              const isShipped = status === 'shipped' || status === 'pre_meeting';
              const canOpen = isShipped && reportTab && onJumpToReport;
              return (
                <li
                  key={key}
                  className="px-5 py-3 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-stone-900">
                      {t(`form.${key}.name`)}
                    </p>
                    <p className="text-[11px] text-stone-500 mt-0.5">
                      {t(`form.${key}.description`)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusPill status={status} />
                    {canOpen && (
                      <button
                        type="button"
                        onClick={() => onJumpToReport(key)}
                        className="px-2.5 py-1 text-[12px] font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 rounded-md transition-colors"
                      >
                        {t('open')}
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {/* Footnote when we showed the implied DOO → dvojno */}
          {data.legal_form === 'DOO' && !data.bookkeeping_system && (
            <p className="px-5 py-2 text-[10px] text-stone-500 italic border-t border-stone-100">
              * {tClients('dooImpliesDvojno')}
            </p>
          )}
        </>
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
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ring-1 ring-inset whitespace-nowrap ${STATUS_CLASSES[status]}`}
    >
      {t(status)}
    </span>
  );
}
