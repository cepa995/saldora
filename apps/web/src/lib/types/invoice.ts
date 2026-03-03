/**
 * TypeScript interfaces mirroring backend invoice schemas.
 *
 * These types are shared across dashboard, invoice list, and detail pages.
 */

export interface CompanyInfo {
  pib: string | null;
  mb: string | null;
  name: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  verified: boolean;
  apr_status: string | null;
}

export interface InvoiceUpdate {
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  seller_pib?: string;
  seller_mb?: string;
  seller_name?: string;
  seller_address?: string;
  seller_city?: string;
  seller_postal_code?: string;
  buyer_pib?: string;
  buyer_mb?: string;
  buyer_name?: string;
  buyer_address?: string;
  buyer_city?: string;
  buyer_postal_code?: string;
  subtotal?: string;
  tax_rate?: string;
  tax_amount?: string;
  total_amount?: string;
  currency?: string;
  line_items?: LineItem[];
  tax_groups?: TaxGroup[];
}

export interface LineItem {
  description: string;
  quantity: string | null;
  unit_price: string | null;
  total: string | null;
  tax_rate: string | null;
  tax_amount: string | null;
}

export interface TaxGroup {
  rate: string;
  base_amount: string;
  tax_amount: string;
}

export interface FieldConfidence {
  field_name: string;
  value: string;
  confidence: number;
  needs_review: boolean;
}

export type InvoiceStatus =
  | 'processing'
  | 'review'
  | 'verified'
  | 'exported'
  | 'error';

export interface InvoiceResponse {
  id: string;
  status: InvoiceStatus;
  confidence_score: number | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  seller: CompanyInfo | null;
  buyer: CompanyInfo | null;
  subtotal: string | null;
  tax_rate: string | null;
  tax_amount: string | null;
  total_amount: string | null;
  currency: string;
  line_items: LineItem[];
  tax_groups: TaxGroup[] | null;
  field_confidences: FieldConfidence[];
  warnings: string[];
  blocked: boolean;
  field_warnings: Record<string, 'error' | 'warning'>;
  accounting_review_needed: boolean | null;
  document_url: string | null;
  raw_ocr_text: string | null;
  raw_llm_output: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginationInfo {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface InvoiceListResponse {
  data: InvoiceResponse[];
  pagination: PaginationInfo;
}

export type SortColumn =
  | 'created_at'
  | 'invoice_date'
  | 'total_amount'
  | 'status'
  | 'confidence_score';

export interface KontoEntry {
  konto: string;
  name: string;
  amount: string;
}

export interface PdvBookEntries {
  book_type: string;
  period: string;
  sequence: number;
  entry_date: string;
  invoice_date: string;
  invoice_number: string;
  counterparty_pib: string;
  counterparty_name: string;
  base_20: string;
  vat_20: string;
  base_10: string;
  vat_10: string;
  total: string;
  pp_pdv_fields: Record<string, string>;
}

export interface AccountingIntentResponse {
  id: string;
  invoice_id: string;
  organization_id: string;
  document_type: string;
  transaction_type: string;
  vat_treatment: string;
  is_deductible: boolean;
  vat_breakdown: Record<string, { base: string; tax: string }>;
  suggested_konta: { debit: KontoEntry[]; credit: KontoEntry[] };
  pdv_book_entries: PdvBookEntries | null;
  confidence: string;
  requires_review: boolean;
  review_reasons: string[];
  reviewed_by: string | null;
  reviewed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type SortOrder = 'asc' | 'desc';

export interface InvoiceFilters {
  page: number;
  per_page: number;
  status?: InvoiceStatus;
  date_from?: string;
  date_to?: string;
  search?: string;
  sort: SortColumn;
  order: SortOrder;
  accounting_review?: boolean;
}
