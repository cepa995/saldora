/**
 * Audit export API service functions.
 *
 * Typed wrappers for audit export endpoints (admin only).
 * Uses apiClient for JSON requests — backend returns presigned S3 URLs.
 */

import { apiClient } from '@/lib/api-client';
import type { AuditExportRequest, AuditExportResponse } from '@/lib/types/audit-export';

/**
 * Create a new audit export ZIP for tax inspection.
 *
 * @param data - Export parameters (date range, content toggles, optional reason).
 * @returns AuditExportResponse with download URL and metadata.
 */
export async function createAuditExport(
  data: AuditExportRequest,
): Promise<AuditExportResponse> {
  return apiClient<AuditExportResponse>('/api/v1/export/audit', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Preview invoice count for a date range before generating.
 *
 * @param dateFrom - Start date (YYYY-MM-DD).
 * @param dateTo - End date (YYYY-MM-DD).
 * @returns Object with invoice_count.
 */
export async function previewAuditExport(
  dateFrom: string,
  dateTo: string,
): Promise<{ invoice_count: number }> {
  return apiClient<{ invoice_count: number }>(
    `/api/v1/export/audit/preview?date_from=${dateFrom}&date_to=${dateTo}`,
  );
}

/**
 * Fetch history of past audit exports for the organization.
 *
 * @returns Array of AuditExportResponse ordered by creation date (newest first).
 */
export async function fetchAuditExportHistory(): Promise<AuditExportResponse[]> {
  return apiClient<AuditExportResponse[]>('/api/v1/export/audit/history');
}
