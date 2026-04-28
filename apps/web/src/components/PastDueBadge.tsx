'use client';

import { pastDueDays } from '@/lib/past_due';
import type { InvoiceResponse } from '@/lib/types/invoice';

interface Props {
  invoice: Pick<InvoiceResponse, 'due_date' | 'invoice_date' | 'status'>;
  /** "dot" keeps it tight for table rows; "full" shows the day count too. */
  variant?: 'dot' | 'full';
}

/**
 * Rose chip that signals "this invoice is past its effective due date."
 * Renders nothing when the invoice is on time.
 */
export function PastDueBadge({ invoice, variant = 'full' }: Props) {
  const days = pastDueDays(invoice);
  if (days <= 0) return null;

  const label = `${days} ${days === 1 ? 'dan' : 'dana'}`;
  const title = `Rok plaćanja prošao pre ${label}.`;

  if (variant === 'dot') {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-rose-50 text-rose-700 ring-1 ring-rose-600/20 tabular-nums whitespace-nowrap shrink-0"
        title={title}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
        {days}d
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 ring-1 ring-rose-600/20 whitespace-nowrap shrink-0"
      title={title}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
      Kasni {label}
    </span>
  );
}
