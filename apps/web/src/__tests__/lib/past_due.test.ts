import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { pastDueDays } from '@/lib/past_due';

type Args = Parameters<typeof pastDueDays>[0];

const FIXED_TODAY = new Date('2026-04-22T12:00:00Z');

describe('pastDueDays', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(FIXED_TODAY);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns 0 when the invoice is due today (not late yet)', () => {
    const invoice: Args = {
      due_date: '2026-04-22',
      invoice_date: '2026-04-01',
      status: 'review',
    };
    expect(pastDueDays(invoice)).toBe(0);
  });

  it('returns positive N when due_date is N days in the past', () => {
    const invoice: Args = {
      due_date: '2026-04-10',
      invoice_date: '2026-03-10',
      status: 'review',
    };
    expect(pastDueDays(invoice)).toBe(12);
  });

  it('returns 0 when due_date is in the future', () => {
    const invoice: Args = {
      due_date: '2026-05-10',
      invoice_date: '2026-04-10',
      status: 'review',
    };
    expect(pastDueDays(invoice)).toBe(0);
  });

  it('falls back to invoice_date when due_date is null', () => {
    // This is the legacy-row path. The OCR worker fills due_date on
    // finalization now, but existing rows may still be null.
    const invoice: Args = {
      due_date: null,
      invoice_date: '2026-04-10',
      status: 'review',
    };
    expect(pastDueDays(invoice)).toBe(12);
  });

  it('returns 0 when both dates are null', () => {
    const invoice: Args = {
      due_date: null,
      invoice_date: null,
      status: 'review',
    };
    expect(pastDueDays(invoice)).toBe(0);
  });

  it('returns 0 when the invoice is exported, regardless of dates', () => {
    // Exported = settled. An exported invoice is never "late" anymore.
    const invoice: Args = {
      due_date: '2026-01-01',
      invoice_date: '2025-12-15',
      status: 'exported',
    };
    expect(pastDueDays(invoice)).toBe(0);
  });

  it.each(['processing', 'review', 'verified', 'error'] as const)(
    'flags a late invoice as past due when status is %s',
    (status) => {
      const invoice: Args = {
        due_date: '2026-04-15',
        invoice_date: '2026-03-15',
        status,
      };
      expect(pastDueDays(invoice)).toBe(7);
    },
  );

  it('returns 0 for malformed date strings', () => {
    const invoice: Args = {
      due_date: 'not-a-date',
      invoice_date: null,
      status: 'review',
    };
    expect(pastDueDays(invoice)).toBe(0);
  });
});
