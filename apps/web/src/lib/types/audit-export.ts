/**
 * Audit export TypeScript types.
 *
 * Mirrors backend schemas: AuditExportRequest and AuditExportResponse
 * from apps/api/app/schemas/export.py.
 */

export interface AuditExportRequest {
  date_from: string;
  date_to: string;
  include_documents: boolean;
  include_audit_trail: boolean;
  include_vat_summary: boolean;
  reason?: string;
}

export interface AuditExportResponse {
  id: string;
  download_url: string | null;
  file_size: number | null;
  invoice_count: number | null;
  period: { from: string; to: string };
  status: 'processing' | 'ready' | 'expired';
  reason: string | null;
  expires_at: string | null;
  created_at: string;
}
