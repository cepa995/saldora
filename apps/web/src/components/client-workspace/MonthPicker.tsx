/**
 * Compact YYYY-MM navigator used in the client workspace header.
 *
 * Clamps to the current month on the forward side — accountants do
 * their work for the current or previous periods, not the future.
 */

'use client';

import { useTranslations } from 'next-intl';

interface Props {
  value: string; // "YYYY-MM"
  onChange: (next: string) => void;
}

function parse(value: string): { year: number; month: number } {
  const [y, m] = value.split('-');
  return { year: Number(y), month: Number(m) };
}

function shift(value: string, delta: number): string {
  const { year, month } = parse(value);
  const idx = (year * 12 + (month - 1)) + delta;
  const y = Math.floor(idx / 12);
  const m = (idx % 12) + 1;
  return `${y}-${String(m).padStart(2, '0')}`;
}

function isFuture(value: string): boolean {
  const { year, month } = parse(value);
  const now = new Date();
  return year > now.getFullYear() || (year === now.getFullYear() && month > now.getMonth() + 1);
}

export function MonthPicker({ value, onChange }: Props) {
  const tCommon = useTranslations('common');
  const tDashboard = useTranslations('dashboard');
  const { year, month } = parse(value);
  const next = shift(value, 1);
  const disableNext = isFuture(next);

  return (
    <div className="inline-flex items-center bg-gray-100 rounded-lg p-0.5">
      <button
        type="button"
        onClick={() => onChange(shift(value, -1))}
        className="p-2 rounded-md hover:bg-white text-gray-600 transition-colors"
        aria-label={tCommon('previous')}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <span className="px-3 text-sm font-semibold text-gray-900 tabular-nums min-w-[110px] text-center">
        {tDashboard(`monthShort.${month}`)} {year}
      </span>
      <button
        type="button"
        onClick={() => onChange(next)}
        disabled={disableNext}
        className="p-2 rounded-md hover:bg-white text-gray-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label={tCommon('next')}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}
