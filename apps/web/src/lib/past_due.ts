import type { InvoiceResponse, InvoiceStatus } from '@/lib/types/invoice';

/**
 * Days an invoice is past its effective due date.
 *
 * * effective_due_date = due_date ?? invoice_date
 *   (the OCR worker coalesces these at finalization; legacy rows may still
 *   have null due_date so the fallback matters).
 * * Returns 0 when the invoice is on time, in the future, exported (settled),
 *   or lacks both dates.
 */
export function pastDueDays(
  invoice: Pick<InvoiceResponse, 'due_date' | 'invoice_date' | 'status'>,
): number {
  if (invoice.status === ('exported' satisfies InvoiceStatus)) return 0;
  const due = invoice.due_date ?? invoice.invoice_date;
  if (!due) return 0;

  const dueDate = new Date(due);
  if (Number.isNaN(dueDate.getTime())) return 0;
  dueDate.setHours(0, 0, 0, 0);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const diff = Math.floor(
    (today.getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24),
  );
  return diff > 0 ? diff : 0;
}
