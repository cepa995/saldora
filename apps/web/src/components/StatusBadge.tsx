'use client';

import { useTranslations } from 'next-intl';
import type { InvoiceStatus } from '@/lib/types/invoice';

const STATUS_CONFIG: Record<
  InvoiceStatus,
  { dotClass: string; badgeClass: string }
> = {
  processing: {
    dotClass: 'bg-amber-500 animate-pulse',
    badgeClass: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20',
  },
  review: {
    dotClass: 'bg-blue-500',
    badgeClass: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20',
  },
  verified: {
    dotClass: 'bg-green-500',
    badgeClass: 'bg-green-50 text-green-700 ring-1 ring-green-600/20',
  },
  exported: {
    dotClass: 'bg-violet-500',
    badgeClass: 'bg-violet-50 text-violet-700 ring-1 ring-violet-600/20',
  },
  error: {
    dotClass: 'bg-red-500',
    badgeClass: 'bg-red-50 text-red-700 ring-1 ring-red-600/20',
  },
};

interface StatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

/**
 * Color-coded status badge with dot indicator and i18n label.
 */
export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const t = useTranslations('status');
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${config.badgeClass} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
      {t(status)}
    </span>
  );
}
