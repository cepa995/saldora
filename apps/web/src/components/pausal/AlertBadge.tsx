/**
 * Alert-level pill used in the paušal dashboard and portfolio.
 * Maps a RevenueStatus alert level to a colored badge in Saldora's palette.
 */

'use client';

import { useTranslations } from 'next-intl';

import type { AlertLevel } from '@/lib/types/pausal';

const STYLES: Record<AlertLevel, { bg: string; text: string; ring: string; dot: string }> = {
  ok: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    ring: 'ring-emerald-200',
    dot: 'bg-emerald-500',
  },
  warning: {
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    ring: 'ring-amber-200',
    dot: 'bg-amber-500',
  },
  critical: {
    bg: 'bg-orange-50',
    text: 'text-orange-800',
    ring: 'ring-orange-200',
    dot: 'bg-orange-500',
  },
  exceeded: {
    bg: 'bg-rose-50',
    text: 'text-rose-800',
    ring: 'ring-rose-200',
    dot: 'bg-rose-500',
  },
};

const LABEL_KEY: Record<AlertLevel, 'alertOk' | 'alertWarning' | 'alertCritical' | 'alertExceeded'> = {
  ok: 'alertOk',
  warning: 'alertWarning',
  critical: 'alertCritical',
  exceeded: 'alertExceeded',
};

interface Props {
  level: AlertLevel;
  size?: 'sm' | 'md';
}

export function AlertBadge({ level, size = 'sm' }: Props) {
  const t = useTranslations('pausal');
  const s = STYLES[level];
  const padding = size === 'md' ? 'px-3 py-1.5 text-sm' : 'px-2.5 py-1 text-xs';
  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full ring-1 ring-inset ${s.bg} ${s.text} ${s.ring} ${padding}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {t(LABEL_KEY[level])}
    </span>
  );
}
