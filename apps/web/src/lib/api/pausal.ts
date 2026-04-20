/**
 * Paušal module API client helpers.
 *
 * Covers customers (buyers of paušal invoices), outgoing invoice issuance,
 * the KPO ledger, revenue status, and the agency portfolio.
 */

import { apiClient } from '@/lib/api-client';
import type {
  Customer,
  CustomerCreate,
  CustomerListResponse,
  KPOEntry,
  KPOListResponse,
  PausalInvoiceIssueRequest,
  PausalInvoiceResponse,
  PortfolioResponse,
  RevenueStatusResponse,
} from '@/lib/types/pausal';

// ---------------------------------------------------------------------------
// Customers
// ---------------------------------------------------------------------------

export async function fetchCustomers(
  clientId: string,
  params: { page?: number; per_page?: number; search?: string; is_active?: boolean } = {},
): Promise<CustomerListResponse> {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', String(params.page));
  if (params.per_page) qs.set('per_page', String(params.per_page));
  if (params.search) qs.set('search', params.search);
  if (params.is_active !== undefined) qs.set('is_active', String(params.is_active));
  const query = qs.toString();
  const url = `/api/v1/pausal/${clientId}/customers${query ? `?${query}` : ''}`;
  return apiClient<CustomerListResponse>(url);
}

export async function createCustomer(
  clientId: string,
  data: CustomerCreate,
): Promise<Customer> {
  return apiClient<Customer>(`/api/v1/pausal/${clientId}/customers`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Issuance
// ---------------------------------------------------------------------------

export async function issueInvoice(
  clientId: string,
  data: PausalInvoiceIssueRequest,
): Promise<PausalInvoiceResponse> {
  return apiClient<PausalInvoiceResponse>(`/api/v1/pausal/${clientId}/invoices`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchInvoicePdfUrl(
  clientId: string,
  invoiceId: string,
): Promise<{ url: string }> {
  return apiClient<{ url: string }>(
    `/api/v1/pausal/${clientId}/invoices/${invoiceId}/pdf`,
  );
}

// ---------------------------------------------------------------------------
// KPO ledger
// ---------------------------------------------------------------------------

export async function fetchKPOEntries(
  clientId: string,
  params: { year?: number; include_cancelled?: boolean; page?: number; per_page?: number } = {},
): Promise<KPOListResponse> {
  const qs = new URLSearchParams();
  if (params.year) qs.set('year', String(params.year));
  if (params.include_cancelled !== undefined)
    qs.set('include_cancelled', String(params.include_cancelled));
  if (params.page) qs.set('page', String(params.page));
  if (params.per_page) qs.set('per_page', String(params.per_page));
  const query = qs.toString();
  return apiClient<KPOListResponse>(
    `/api/v1/pausal/${clientId}/kpo${query ? `?${query}` : ''}`,
  );
}

export async function stornoKPO(
  clientId: string,
  entryId: string,
  notes?: string,
): Promise<KPOEntry> {
  return apiClient<KPOEntry>(
    `/api/v1/pausal/${clientId}/kpo/${entryId}/storno`,
    {
      method: 'POST',
      body: JSON.stringify({ notes: notes ?? null }),
    },
  );
}

// ---------------------------------------------------------------------------
// Revenue status
// ---------------------------------------------------------------------------

export async function fetchRevenueStatus(
  clientId: string,
  year?: number,
): Promise<RevenueStatusResponse> {
  const qs = year ? `?year=${year}` : '';
  return apiClient<RevenueStatusResponse>(
    `/api/v1/pausal/${clientId}/revenue-status${qs}`,
  );
}

export async function fetchPortfolio(year?: number): Promise<PortfolioResponse> {
  const qs = year ? `?year=${year}` : '';
  return apiClient<PortfolioResponse>(`/api/v1/pausal/portfolio${qs}`);
}

// ---------------------------------------------------------------------------
// Outgoing invoice list (paušal-issued)
// ---------------------------------------------------------------------------

export interface OutgoingInvoiceListResponse {
  data: Array<{
    id: string;
    status: string;
    direction: string;
    invoice_number: string | null;
    invoice_date: string | null;
    total_amount: string | null;
    currency: string;
    client_id: string | null;
    client: { id: string; name: string; pib: string } | null;
  }>;
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export async function fetchOutgoingInvoices(
  clientId: string,
  params: { page?: number; per_page?: number } = {},
): Promise<OutgoingInvoiceListResponse> {
  const qs = new URLSearchParams({ direction: 'outgoing', client_id: clientId });
  if (params.page) qs.set('page', String(params.page));
  if (params.per_page) qs.set('per_page', String(params.per_page));
  return apiClient<OutgoingInvoiceListResponse>(`/api/v1/invoices?${qs.toString()}`);
}
