/**
 * Revenue status card showing the paušalac's YTD revenue against the
 * two legal thresholds (6M RSD paušal status + 8M RSD PDV registration).
 *
 * Designed for the per-client dashboard (M14.7). Uses a gradient hero
 * panel with two stacked progress bars and a prominent total.
 */

'use client';

import { useTranslations } from 'next-intl';

import type { RevenueStatusResponse } from '@/lib/types/pausal';

import { AlertBadge } from './AlertBadge';

function fmtRsd(amount: string | number, withSuffix = true): string {
  const num = typeof amount === 'string' ? Number(amount) : amount;
  const formatted = new Intl.NumberFormat('sr-Latn-RS', {
    maximumFractionDigits: 0,
  }).format(Math.round(num));
  return withSuffix ? `${formatted} RSD` : formatted;
}

interface Props {
  data: RevenueStatusResponse | null;
  isLoading: boolean;
}

const BAR_COLORS = {
  ok: { fill: 'bg-emerald-500', track: 'bg-emerald-100' },
  warning: { fill: 'bg-amber-500', track: 'bg-amber-100' },
  critical: { fill: 'bg-orange-500', track: 'bg-orange-100' },
  exceeded: { fill: 'bg-rose-500', track: 'bg-rose-100' },
} as const;

function ThresholdBar({
  label,
  used_pct,
  remaining,
  limit,
  level,
}: {
  label: string;
  used_pct: number;
  remaining: string;
  limit: string;
  level: 'ok' | 'warning' | 'critical' | 'exceeded';
}) {
  const clamped = Math.min(used_pct, 100);
  const colors = BAR_COLORS[level];
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-xs text-gray-500 tabular-nums">
          {fmtRsd(remaining)} /{' '}
          <span className="text-gray-400">{fmtRsd(limit)}</span>
        </span>
      </div>
      <div className={`relative h-3 rounded-full overflow-hidden ${colors.track}`}>
        <div
          className={`absolute inset-y-0 left-0 rounded-full ${colors.fill} transition-all duration-500 ease-out`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-1.5">
        <span className="text-xs font-semibold text-gray-900 tabular-nums">
          {used_pct.toFixed(1)}%
        </span>
        <AlertBadge level={level} />
      </div>
    </div>
  );
}

export function RevenueStatusCard({ data, isLoading }: Props) {
  const t = useTranslations('pausal');

  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-6 animate-pulse">
        <div className="h-5 bg-gray-100 rounded w-32 mb-4" />
        <div className="h-10 bg-gray-100 rounded w-48 mb-6" />
        <div className="space-y-4">
          <div className="h-3 bg-gray-100 rounded" />
          <div className="h-3 bg-gray-100 rounded" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { year, total_revenue, thresholds, overall_alert_level, non_rsd_count } = data;
  const pausalStatus = thresholds.pausal_status;
  const pdv = thresholds.pdv;

  return (
    <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-violet-700 to-indigo-800 text-white shadow-lg shadow-violet-900/10 overflow-hidden">
      <div className="p-6 sm:p-7">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <p className="text-violet-200 text-xs font-semibold tracking-wider uppercase">
              {t('revenueStatus')}
            </p>
            <p className="text-violet-100 text-sm mt-1">
              {t('revenueStatusSubtitle', { year: String(year) })}
            </p>
          </div>
          <AlertBadge level={overall_alert_level} size="md" />
        </div>

        <div className="flex items-baseline gap-2 mb-6">
          <span className="text-4xl sm:text-5xl font-bold tabular-nums tracking-tight">
            {fmtRsd(total_revenue, false)}
          </span>
          <span className="text-violet-200 font-medium">RSD</span>
        </div>

        <div className="bg-white rounded-xl p-5 space-y-5 text-gray-900 shadow-lg shadow-violet-900/20">
          <ThresholdBar
            label={t('pausalStatusLimit')}
            used_pct={pausalStatus.used_pct}
            remaining={pausalStatus.remaining}
            limit={pausalStatus.limit}
            level={pausalStatus.alert_level}
          />
          <ThresholdBar
            label={t('pdvThresholdLimit')}
            used_pct={pdv.used_pct}
            remaining={pdv.remaining}
            limit={pdv.limit}
            level={pdv.alert_level}
          />
        </div>

        {non_rsd_count > 0 && (
          <p className="mt-4 text-xs text-amber-100 bg-amber-500/15 border border-amber-300/20 rounded-lg px-3 py-2">
            {t('nonRsdWarning', { count: String(non_rsd_count) })}
          </p>
        )}
      </div>
    </div>
  );
}
