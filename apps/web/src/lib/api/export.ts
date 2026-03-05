/**
 * Export API service functions.
 *
 * Typed wrappers for export-related endpoints.
 * Uses apiDownload for binary file responses.
 */

import { apiClient, apiDownload } from '@/lib/api-client';
import type { ExportFormat, ExportOptions, MiniMaxPushResponse } from '@/lib/types/export';

/**
 * Export invoices to the specified format.
 *
 * @param format - Target format (xlsx, csv, json, minimax_xml).
 * @param invoiceIds - Array of invoice UUIDs to export.
 * @param options - Format-specific export options.
 * @returns Object with blob data and filename for download.
 */
const FORMAT_EXTENSIONS: Record<ExportFormat, string> = {
  xlsx: 'xlsx',
  csv: 'csv',
  json: 'json',
  minimax_xml: 'xml',
};

export async function exportInvoices(
  format: ExportFormat,
  invoiceIds: string[],
  options?: ExportOptions,
): Promise<{ blob: Blob; filename: string }> {
  const result = await apiDownload('/api/v1/export', {
    method: 'POST',
    body: JSON.stringify({
      format,
      invoice_ids: invoiceIds,
      options: options ?? {},
    }),
  });
  // If Content-Disposition was not exposed by CORS, ensure correct extension
  if (!result.filename.includes('.')) {
    result.filename = `${result.filename}.${FORMAT_EXTENSIONS[format]}`;
  }
  return result;
}

/**
 * Trigger a file download in the browser from a Blob.
 *
 * Creates a temporary object URL, triggers click on a hidden anchor,
 * then revokes the URL to free memory.
 *
 * @param blob - File blob data.
 * @param filename - Suggested filename for the download.
 */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => URL.revokeObjectURL(url), 100);
}

/**
 * Push invoices to MiniMax accounting software via REST API.
 *
 * @param invoiceIds - Array of invoice UUIDs to push.
 * @param createCustomers - Create customers in MiniMax if not found.
 * @returns Push results per invoice with success/error status.
 */
export async function pushToMinimax(
  invoiceIds: string[],
  createCustomers: boolean = true,
): Promise<MiniMaxPushResponse> {
  return apiClient<MiniMaxPushResponse>('/api/v1/export/minimax/push', {
    method: 'POST',
    body: JSON.stringify({
      invoice_ids: invoiceIds,
      create_customers: createCustomers,
    }),
  });
}
