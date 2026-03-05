/**
 * Serbian-locale formatting utilities for dates, numbers, and relative time.
 */

/**
 * Format an ISO date string to Serbian DD.MM.YYYY. format.
 *
 * Args:
 *   dateStr - ISO date string (e.g. "2026-01-15") or null.
 * Returns:
 *   Formatted date string or em-dash for null/invalid values.
 */
export function formatDateSr(dateStr: string | null): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '—';
  const day = String(d.getUTCDate()).padStart(2, '0');
  const month = String(d.getUTCMonth() + 1).padStart(2, '0');
  const year = d.getUTCFullYear();
  return `${day}.${month}.${year}.`;
}

/**
 * Format a numeric value to Serbian locale (e.g. 45.000,00 RSD).
 *
 * Args:
 *   value - Number or string representation of the amount, or null.
 *   currency - Optional currency code to append (e.g. "RSD").
 * Returns:
 *   Formatted amount string or em-dash for null/invalid values.
 */
export function formatAmountSr(
  value: string | number | null,
  currency?: string,
): string {
  if (value === null || value === undefined) return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';
  const formatted = num.toLocaleString('sr-Latn-RS', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return currency ? `${formatted} ${currency}` : formatted;
}

/**
 * Format an ISO datetime string to a relative time description in Serbian.
 *
 * Args:
 *   dateStr - ISO datetime string (e.g. "2026-02-26T10:30:00Z").
 * Returns:
 *   Relative time string: "upravo", "pre X min", "pre X sati",
 *   "juče", or falls back to DD.MM.YYYY. for older dates.
 */
export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '—';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'upravo';
  if (diffMin < 60) return `pre ${diffMin} min`;
  if (diffHours < 24) return `pre ${diffHours} ${diffHours === 1 ? 'sat' : diffHours < 5 ? 'sata' : 'sati'}`;
  if (diffDays === 1) return 'juče';
  if (diffDays < 7) return `pre ${diffDays} ${diffDays < 5 ? 'dana' : 'dana'}`;

  return formatDateSr(dateStr);
}

/**
 * Format a byte count to human-readable size string in Serbian locale.
 *
 * Args:
 *   bytes - File size in bytes, or null.
 * Returns:
 *   Formatted string (e.g. "2,3 MB") or em-dash for null values.
 */
export function formatFileSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1);
  const value = bytes / Math.pow(k, i);

  return `${value.toLocaleString('sr-Latn-RS', {
    minimumFractionDigits: i > 1 ? 1 : 0,
    maximumFractionDigits: 1,
  })} ${units[i]}`;
}
