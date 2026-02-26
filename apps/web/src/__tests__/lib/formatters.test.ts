import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatDateSr, formatAmountSr, formatRelativeTime } from '@/lib/formatters';

describe('formatDateSr', () => {
  it('formats a valid ISO date to DD.MM.YYYY.', () => {
    expect(formatDateSr('2026-01-15')).toBe('15.01.2026.');
  });

  it('formats single-digit day and month with leading zeros', () => {
    expect(formatDateSr('2026-03-05')).toBe('05.03.2026.');
  });

  it('returns em-dash for null', () => {
    expect(formatDateSr(null)).toBe('—');
  });

  it('returns em-dash for empty string', () => {
    expect(formatDateSr('')).toBe('—');
  });

  it('returns em-dash for invalid date string', () => {
    expect(formatDateSr('not-a-date')).toBe('—');
  });

  it('handles a date at the end of year', () => {
    expect(formatDateSr('2026-12-31')).toBe('31.12.2026.');
  });
});

describe('formatAmountSr', () => {
  it('formats a numeric value with Serbian locale', () => {
    const result = formatAmountSr(45000);
    // Serbian locale uses dot as thousands separator and comma for decimal
    expect(result).toMatch(/45/);
    expect(result).toMatch(/00$/);
  });

  it('formats a string value', () => {
    const result = formatAmountSr('1234.56');
    expect(result).toMatch(/1/);
    expect(result).toMatch(/234/);
    expect(result).toMatch(/56/);
  });

  it('appends currency code when provided', () => {
    const result = formatAmountSr(1000, 'RSD');
    expect(result).toContain('RSD');
  });

  it('returns em-dash for null', () => {
    expect(formatAmountSr(null)).toBe('—');
  });

  it('returns em-dash for NaN string', () => {
    expect(formatAmountSr('abc')).toBe('—');
  });

  it('formats zero correctly', () => {
    const result = formatAmountSr(0);
    expect(result).toMatch(/0/);
  });
});

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-26T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "upravo" for less than 1 minute ago', () => {
    expect(formatRelativeTime('2026-02-26T12:00:00Z')).toBe('upravo');
  });

  it('returns minutes for less than 60 minutes', () => {
    expect(formatRelativeTime('2026-02-26T11:45:00Z')).toBe('pre 15 min');
  });

  it('returns hours for less than 24 hours (singular)', () => {
    expect(formatRelativeTime('2026-02-26T11:00:00Z')).toBe('pre 1 sat');
  });

  it('returns hours for less than 24 hours (plural 2-4)', () => {
    expect(formatRelativeTime('2026-02-26T09:00:00Z')).toBe('pre 3 sata');
  });

  it('returns hours for less than 24 hours (plural 5+)', () => {
    expect(formatRelativeTime('2026-02-26T02:00:00Z')).toBe('pre 10 sati');
  });

  it('returns "juče" for yesterday', () => {
    expect(formatRelativeTime('2026-02-25T12:00:00Z')).toBe('juče');
  });

  it('returns days for less than a week', () => {
    expect(formatRelativeTime('2026-02-23T12:00:00Z')).toBe('pre 3 dana');
  });

  it('returns formatted date for older dates', () => {
    expect(formatRelativeTime('2026-01-15T10:00:00Z')).toBe('15.01.2026.');
  });

  it('returns em-dash for invalid date', () => {
    expect(formatRelativeTime('invalid')).toBe('—');
  });
});
