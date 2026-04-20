/**
 * TypeScript interfaces for the paušal module.
 * Mirrors backend schemas under app/schemas/{customer,pausal_invoice,kpo,revenue}.py.
 */

export type AlertLevel = 'ok' | 'warning' | 'critical' | 'exceeded';

export interface Customer {
  id: string;
  client_id: string;
  name: string;
  is_natural_person: boolean;
  pib: string | null;
  mb: string | null;
  jmbg: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  country: string;
  contact_email: string | null;
  contact_phone: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerCreate {
  name: string;
  is_natural_person?: boolean;
  pib?: string;
  mb?: string;
  jmbg?: string;
  address?: string;
  city?: string;
  postal_code?: string;
  country?: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
}

export interface CustomerListResponse {
  data: Customer[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export interface PausalInvoiceItem {
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
}

export interface PausalInvoiceIssueRequest {
  customer_id?: string | null;
  new_customer?: CustomerCreate | null;
  invoice_date: string;
  due_date?: string | null;
  place_of_issue: string;
  delivery_date?: string | null;
  delivery_place?: string | null;
  items: PausalInvoiceItem[];
  currency?: string;
  notes?: string | null;
}

export interface PausalInvoiceResponse {
  id: string;
  invoice_number: string;
  status: string;
  direction: string;
  client_id: string;
  customer_snapshot: Record<string, unknown>;
  seller_snapshot: Record<string, unknown>;
  invoice_date: string;
  due_date: string | null;
  items: Record<string, string>[];
  currency: string;
  subtotal: string;
  total_amount: string;
  notes: string | null;
  pdf_url: string | null;
  created_at: string;
}

export interface KPOEntry {
  id: string;
  client_id: string;
  invoice_id: string | null;
  storno_of_id: string | null;
  year: number;
  entry_number: string;
  entry_date: string;
  invoice_number: string | null;
  customer_name: string;
  customer_pib: string | null;
  amount: string;
  currency: string;
  notes: string | null;
  is_cancelled: boolean;
  created_at: string;
  updated_at: string;
}

export interface KPOListResponse {
  data: KPOEntry[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export interface ThresholdStatus {
  limit: string;
  used_pct: number;
  remaining: string;
  alert_level: AlertLevel;
}

export interface RevenueStatusResponse {
  year: number;
  currency: string;
  total_revenue: string;
  thresholds: {
    pausal_status: ThresholdStatus;
    pdv: ThresholdStatus;
  };
  overall_alert_level: AlertLevel;
  non_rsd_count: number;
}

export interface PortfolioRow {
  client_id: string;
  name: string;
  pib: string;
  activity_code: string | null;
  total_revenue: string;
  pausal_status_pct: number;
  pdv_pct: number;
  overall_alert_level: AlertLevel;
  non_rsd_count: number;
}

export interface PortfolioResponse {
  year: number;
  data: PortfolioRow[];
}
