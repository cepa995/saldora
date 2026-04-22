'use client';

import Link from 'next/link';

import { formatAmountSr } from '@/lib/formatters';
import { useOrgPath } from '@/lib/navigation';

interface Props {
  /** Number of past-due invoices across the agency, right now. */
  count: number;
  /** Sum of their total_amount in RSD. */
  totalRsd: number;
  /** Max days-late across the past-due set. */
  oldestDays: number;
}

/**
 * Agency-wide past-due summary strip. Renders three stats side by side —
 * count, total RSD, oldest-days-late — and a call-to-action linking into
 * /invoices pre-filtered to past-due. Caller decides when to render (we
 * hide it when count === 0).
 */
export function PastDueRollup({ count, totalRsd, oldestDays }: Props) {
  const orgPath = useOrgPath();

  return (
    <section className="rounded-2xl border border-rose-200 bg-rose-50/50 overflow-hidden">
      <div className="px-6 py-4 border-b border-rose-200/60 flex items-center justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-700 flex items-center justify-center shrink-0 mt-0.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="min-w-0">
            <h2 className="font-semibold text-rose-900">Kasne fakture — pregled</h2>
            <p className="text-xs text-rose-700/80 mt-0.5">
              Zbir svih neokončanih faktura čiji je rok plaćanja prošao.
            </p>
          </div>
        </div>
        <Link
          href={orgPath('/invoices?past_due=true')}
          className="shrink-0 inline-flex items-center gap-1.5 text-sm font-medium text-rose-700 hover:text-rose-900 transition-colors"
        >
          Pogledaj sve
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </Link>
      </div>

      <div className="grid grid-cols-3 divide-x divide-rose-200/60">
        <Stat label="Ukupno" value={count.toLocaleString('sr-Latn')} />
        <Stat
          label="Iznos"
          value={totalRsd > 0 ? formatAmountSr(String(totalRsd), 'RSD') : '—'}
          hint={totalRsd > 0 ? 'RSD' : undefined}
        />
        <Stat
          label="Najstarija"
          value={oldestDays > 0 ? `${oldestDays}` : '—'}
          hint={oldestDays > 0 ? (oldestDays === 1 ? 'dan' : 'dana') : undefined}
        />
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="px-5 py-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-rose-700/70">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-rose-900 tabular-nums leading-tight">
        {value}
        {hint && (
          <span className="ml-1 text-sm font-medium text-rose-700/70 align-baseline">
            {hint}
          </span>
        )}
      </p>
    </div>
  );
}
