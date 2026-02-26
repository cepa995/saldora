/**
 * TypeScript interfaces mirroring backend invoice schemas.
 *
 * These types are shared across dashboard, invoice list, and detail pages.
 */

export interface CompanyInfo {
  pib: string;
  name: string;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  verified: boolean;
  apr_status: string | null;
}

export interface LineItem {
  description: string;
  quantity: string;
  unit_price: string;
  total: string;
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
  document_url: string | null;
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
