/**
 * PDV Books (KPR/KIR) API service functions.
 *
 * Typed wrappers for PDV book generation endpoints.
 */

import { apiClient, apiDownload } from '@/lib/api-client';

interface PdvBookPreviewResponse {
  entry_count: number;
  period: string;
  book_type: string;
}

/**
 * Preview entry count for a KPR/KIR book period.
 *
 * Args:
 *   bookType - KPR or KIR.
 *   period - Period in YYYY-MM format.
 *   clientId - Optional client filter for agency users.
 * Returns:
 *   Preview response with entry count.
 */
export async function previewPdvBook(
  bookType: string,
  period: string,
  clientId?: string,
): Promise<PdvBookPreviewResponse> {
  const params = new URLSearchParams({ book_type: bookType, period });
  if (clientId) params.set('client_id', clientId);
  return apiClient<PdvBookPreviewResponse>(
    `/api/v1/export/pdv-books/preview?${params.toString()}`,
  );
}

/**
 * Generate and download a KPR/KIR book.
 *
 * Args:
 *   bookType - KPR or KIR.
 *   period - Period in YYYY-MM format.
 *   format - Export format: xlsx or csv.
 *   clientId - Optional client filter for agency users.
 * Returns:
 *   Blob and filename for download.
 */
export async function generatePdvBook(
  bookType: string,
  period: string,
  format: string = 'xlsx',
  clientId?: string,
): Promise<{ blob: Blob; filename: string }> {
  return apiDownload('/api/v1/export/pdv-books', {
    method: 'POST',
    body: JSON.stringify({
      book_type: bookType,
      period,
      format,
      ...(clientId ? { client_id: clientId } : {}),
    }),
  });
}
