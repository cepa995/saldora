/**
 * Export-related TypeScript types.
 *
 * Mirrors the backend schemas in apps/api/app/schemas/export.py.
 */

export type ExportFormat = 'xlsx' | 'csv' | 'json' | 'minimax_xml';

export interface ExportOptions {
  include_line_items?: boolean;
  nested_json?: boolean;
  date_format?: string;
  decimal_separator?: string;
  delimiter?: string;
}

export interface ExportRequest {
  format: ExportFormat;
  invoice_ids: string[];
  template_id?: string;
  options?: ExportOptions;
}

export interface BlockedInvoice {
  invoice_id: string;
  invoice_number: string | null;
  reasons: string[];
}

export interface MiniMaxPushResult {
  invoice_id: string;
  invoice_number: string | null;
  minimax_id: number | null;
  status: 'success' | 'error';
  error: string | null;
}

export interface MiniMaxPushResponse {
  results: MiniMaxPushResult[];
  total: number;
  success_count: number;
  error_count: number;
}
