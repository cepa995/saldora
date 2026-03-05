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

export interface ExportTemplate {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  fields: { key: string; label: string; order: number }[];
  supported_formats: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ExportTemplateCreate {
  name: string;
  description?: string;
  fields: { key: string; label: string; order: number }[];
  supported_formats?: string[];
}

export interface ExportTemplateUpdate {
  name?: string;
  description?: string;
  fields?: { key: string; label: string; order: number }[];
  supported_formats?: string[];
}
