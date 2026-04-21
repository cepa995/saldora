/**
 * Timeline tab contents for the client workspace.
 *
 * Renders the ``client_events`` stream for one client, scoped to a
 * YYYY-MM period. Rows are grouped by day; each row has a type-
 * specific icon/color, a short description derived from the payload,
 * and (when available) a click-through to the underlying entity.
 */

'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { MonthPicker } from '@/components/client-workspace/MonthPicker';
import { FilterPill, type PillTone } from '@/components/clients/FilterPill';
import type { ClientEventResponse } from '@/lib/api/clients';
import { fetchClientEvents } from '@/lib/api/clients';
import { useOrgPath } from '@/lib/navigation';

interface Props {
  clientId: string;
}

function currentYYYYMM(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

const EVENT_TYPES = [
  'invoice_uploaded',
  'invoice_verified',
  'invoice_exported',
  'client_assigned',
] as const;

type EventType = (typeof EVENT_TYPES)[number];

const ICON_BG: Record<string, string> = {
  invoice_uploaded: 'bg-blue-50 text-blue-600 ring-blue-100',
  invoice_verified: 'bg-emerald-50 text-emerald-600 ring-emerald-100',
  invoice_exported: 'bg-violet-50 text-violet-600 ring-violet-100',
  client_assigned: 'bg-amber-50 text-amber-600 ring-amber-100',
};

const TYPE_TONE: Record<EventType, PillTone> = {
  invoice_uploaded: 'blue',
  invoice_verified: 'emerald',
  invoice_exported: 'violet',
  client_assigned: 'amber',
};

const FALLBACK_ICON_BG = 'bg-gray-50 text-gray-500 ring-gray-100';

function EventIcon({ type }: { type: string }) {
  const base = `w-8 h-8 rounded-full ring-1 ring-inset flex items-center justify-center flex-shrink-0 ${
    ICON_BG[type] ?? FALLBACK_ICON_BG
  }`;
  if (type === 'invoice_uploaded') {
    return (
      <span className={base}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
      </span>
    );
  }
  if (type === 'invoice_verified') {
    return (
      <span className={base}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </span>
    );
  }
  if (type === 'invoice_exported') {
    return (
      <span className={base}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17l10-10M7 7h10v10" />
        </svg>
      </span>
    );
  }
  if (type === 'client_assigned') {
    return (
      <span className={base}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7a4 4 0 11-8 0 4 4 0 018 0zM9 14a6 6 0 00-6 6v1h12v-1a6 6 0 00-6-6zM21 12h-6m3-3v6" />
        </svg>
      </span>
    );
  }
  return (
    <span className={base}>
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01" />
      </svg>
    </span>
  );
}

function formatDayHeader(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('sr-Latn-RS', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('sr-Latn-RS', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function groupByDay(events: ClientEventResponse[]): Array<{ day: string; rows: ClientEventResponse[] }> {
  const groups = new Map<string, ClientEventResponse[]>();
  for (const e of events) {
    const day = e.event_date.slice(0, 10);
    const list = groups.get(day) ?? [];
    list.push(e);
    groups.set(day, list);
  }
  // Preserve event order (already newest-first from the API)
  return Array.from(groups.entries()).map(([day, rows]) => ({ day, rows }));
}

function describe(e: ClientEventResponse, t: (k: string, v?: Record<string, string>) => string): string {
  const invoiceNumber = (e.payload?.invoice_number as string | undefined) ?? '';
  switch (e.event_type) {
    case 'invoice_uploaded':
      return t('descInvoiceUploaded', { filename: (e.payload?.filename as string) ?? '' });
    case 'invoice_verified':
      return t('descInvoiceVerified', { invoiceNumber });
    case 'invoice_exported':
      return t('descInvoiceExported', {
        invoiceNumber,
        destination: (e.payload?.destination as string) ?? 'export',
      });
    case 'client_assigned':
      return e.payload?.auto_assigned
        ? t('descClientAutoAssigned', { invoiceNumber })
        : t('descClientAssigned', { invoiceNumber });
    default:
      return e.event_type;
  }
}

export function ClientTimeline({ clientId }: Props) {
  const t = useTranslations('clientWorkspace');
  const tCommon = useTranslations('common');
  const orgPath = useOrgPath();

  const [period, setPeriod] = useState<string>(currentYYYYMM());
  const [events, setEvents] = useState<ClientEventResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterTypes, setFilterTypes] = useState<Set<EventType>>(new Set());

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetchClientEvents(clientId, { period, per_page: 200 });
      setEvents(resp.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, period, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    if (filterTypes.size === 0) return events;
    return events.filter((e) => filterTypes.has(e.event_type as EventType));
  }, [events, filterTypes]);

  const groups = useMemo(() => groupByDay(filtered), [filtered]);

  function toggleType(tp: EventType) {
    setFilterTypes((prev) => {
      const next = new Set(prev);
      if (next.has(tp)) next.delete(tp);
      else next.add(tp);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      {/* Toolbar: period picker on the left, type filters on the right */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <MonthPicker value={period} onChange={setPeriod} />
        <div className="flex flex-wrap gap-2 sm:ml-auto">
          <FilterPill
            label={tCommon('all')}
            active={filterTypes.size === 0}
            tone="neutral"
            onClick={() => setFilterTypes(new Set())}
          />
          {EVENT_TYPES.map((tp) => (
            <FilterPill
              key={tp}
              label={t(`eventType_${tp}`)}
              active={filterTypes.has(tp)}
              tone={TYPE_TONE[tp]}
              onClick={() => toggleType(tp)}
            />
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm">
          {error}
        </div>
      )}

      {isLoading && events.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-sm text-gray-500 text-center">
          {tCommon('loading')}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center">
          <div className="w-10 h-10 rounded-full bg-gray-100 text-gray-400 mx-auto mb-3 flex items-center justify-center">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-sm text-gray-500">{t('timelineEmpty')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map(({ day, rows }) => (
            <section key={day}>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 sticky top-0 bg-gray-50/90 backdrop-blur-sm py-1">
                {formatDayHeader(day)}
              </h3>
              <ul className="space-y-2">
                {rows.map((e) => (
                  <li
                    key={e.id}
                    className="flex items-start gap-3 p-3 rounded-xl bg-white border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all"
                  >
                    <EventIcon type={e.event_type} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-900">
                        {describe(e, t)}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5 tabular-nums">
                        {formatTime(e.event_date)}
                      </p>
                    </div>
                    {e.entity_type === 'invoice' && e.entity_id && (
                      <Link
                        href={orgPath(`/invoices/${e.entity_id}`)}
                        className="self-center text-xs font-medium text-violet-700 hover:text-violet-900 opacity-0 group-hover:opacity-100"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
