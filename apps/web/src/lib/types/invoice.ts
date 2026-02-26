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
}

export interface LineItem {
  description: string;
  quantity: string | null;
  unit_price: string | null;
  total: string | null;
  tax_rate: string | null;
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
  field_confidences: FieldConfidence[];
  warnings: string[];
  blocked: boolean;
  field_warnings: Record<string, 'error' | 'warning'>;
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
}
