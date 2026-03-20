/**
 * Export API service functions.
 *
 * Typed wrappers for export-related endpoints.
 * Uses apiDownload for binary file responses.
 */

import { apiClient, apiDownload } from '@/lib/api-client';
import type {
  ExportFormat,
  ExportOptions,
  ExportTemplate,
  ExportTemplateCreate,
  ExportTemplateUpdate,
  MiniMaxPushResponse,
  MiniMaxConfig,
  MiniMaxConfigCreate,
} from '@/lib/types/export';

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

/**
 * Fetch available export templates for the current organization.
 *
 * @returns Array of export templates (system defaults + custom).
 */
export async function fetchTemplates(): Promise<ExportTemplate[]> {
  return apiClient<ExportTemplate[]>('/api/v1/export/templates');
}

/**
 * Create a custom export template.
 *
 * @param data - Template definition with name, fields, and formats.
 * @returns The created template.
 */
export async function createTemplate(data: ExportTemplateCreate): Promise<ExportTemplate> {
  return apiClient<ExportTemplate>('/api/v1/export/templates', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update a custom export template.
 *
 * @param id - Template UUID.
 * @param data - Fields to update.
 * @returns The updated template.
 */
export async function updateTemplate(id: string, data: ExportTemplateUpdate): Promise<ExportTemplate> {
  return apiClient<ExportTemplate>(`/api/v1/export/templates/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a custom export template.
 *
 * @param id - Template UUID.
 */
export async function deleteTemplate(id: string): Promise<void> {
  return apiClient<void>(`/api/v1/export/templates/${id}`, {
    method: 'DELETE',
  });
}

export async function exportInvoices(
  format: ExportFormat,
  invoiceIds: string[],
  options?: ExportOptions,
  templateId?: string,
  skipValidation?: boolean,
): Promise<{ blob: Blob; filename: string }> {
  const body: Record<string, unknown> = {
    format,
    invoice_ids: invoiceIds,
    options: options ?? {},
  };
  if (templateId && templateId !== 'default') {
    body.template_id = templateId;
  }
  if (skipValidation) {
    body.skip_validation = true;
  }
  const result = await apiDownload('/api/v1/export', {
    method: 'POST',
    body: JSON.stringify(body),
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
 * Fetch the MiniMax integration config for the current organization.
 *
 * @returns The MiniMax config object.
 */
export async function fetchMiniMaxConfig(): Promise<MiniMaxConfig> {
  return apiClient<MiniMaxConfig>('/api/v1/export/minimax/config');
}

/**
 * Create or update the MiniMax integration config.
 *
 * @param data - MiniMax credentials and org ID.
 * @returns The saved MiniMax config.
 */
export async function saveMiniMaxConfig(data: MiniMaxConfigCreate): Promise<MiniMaxConfig> {
  return apiClient<MiniMaxConfig>('/api/v1/export/minimax/config', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Test the MiniMax connection using saved credentials.
 *
 * @returns Status and message from the test.
 */
export async function testMiniMaxConnection(): Promise<{ status: string; message: string }> {
  return apiClient<{ status: string; message: string }>('/api/v1/export/minimax/test-connection', {
    method: 'POST',
  });
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
