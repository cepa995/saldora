import { apiClient } from '@/lib/api-client';

export interface ExportLog {
  id: string;
  period: string;
  delivery_method: string;
  delivered_to: string;
  file_size_bytes: number | null;
  invoice_count: number | null;
  status: string;
  error_message: string | null;
  delivered_at: string;
}

export interface ArchiveSettings {
  enabled: boolean;
  email: string;
  formats: string[];
  include_pdfs: boolean;
}

export interface ArchiveResult {
  status: string;
  period: string;
  delivered_to: string;
  invoice_count: number;
  file_size: number;
  download_url: string;
}

/**
 * Fetch the monthly archive export history for the current organization.
 *
 * Returns:
 *   List of export log entries ordered by most recent first.
 */
export async function fetchExportHistory(): Promise<ExportLog[]> {
  return apiClient<ExportLog[]>('/api/v1/archive/history');
}

/**
 * Fetch the current monthly archive settings for the organization.
 *
 * Returns:
 *   Current archive settings including enabled state and delivery email.
 */
export async function fetchArchiveSettings(): Promise<ArchiveSettings> {
  return apiClient<ArchiveSettings>('/api/v1/archive/settings');
}

/**
 * Update monthly archive settings.
 *
 * Args:
 *   enabled: Whether automatic monthly export is active.
 *   includePdfs: Whether to include original PDF documents in the archive.
 *
 * Returns:
 *   Updated archive settings.
 */
export async function updateArchiveSettings(enabled: boolean, includePdfs: boolean): Promise<ArchiveSettings> {
  return apiClient<ArchiveSettings>(`/api/v1/archive/settings?enabled=${enabled}&include_pdfs=${includePdfs}`, { method: 'PUT' });
}

/**
 * Trigger a manual archive export for the given period.
 *
 * Args:
 *   period: Month period in YYYY-MM format (e.g. "2025-03").
 *
 * Returns:
 *   Result of the export generation including download URL.
 */
export async function triggerArchiveExport(period: string): Promise<ArchiveResult> {
  return apiClient<ArchiveResult>(`/api/v1/archive/generate?period=${period}`, { method: 'POST' });
}
