import type { InvoiceStatus } from '@/lib/types/invoice';

const STATUS_CONFIG: Record<
  InvoiceStatus,
  { label: string; dotClass: string; badgeClass: string }
> = {
  processing: {
    label: 'Obrada',
    dotClass: 'bg-amber-500 animate-pulse',
    badgeClass: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20',
  },
  review: {
    label: 'Pregled',
    dotClass: 'bg-blue-500',
    badgeClass: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20',
  },
  verified: {
    label: 'Verifikovano',
    dotClass: 'bg-green-500',
    badgeClass: 'bg-green-50 text-green-700 ring-1 ring-green-600/20',
  },
  exported: {
    label: 'Izvezeno',
    dotClass: 'bg-violet-500',
    badgeClass: 'bg-violet-50 text-violet-700 ring-1 ring-violet-600/20',
  },
  error: {
    label: 'Greška',
    dotClass: 'bg-red-500',
    badgeClass: 'bg-red-50 text-red-700 ring-1 ring-red-600/20',
  },
};

interface StatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

/**
 * Color-coded status badge with dot indicator.
 *
 * Args:
 *   status - Invoice lifecycle status.
 *   className - Additional CSS classes.
 */
export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${config.badgeClass} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
      {config.label}
    </span>
  );
}
