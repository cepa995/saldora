/**
 * Invoice API service functions.
 *
 * Typed wrappers around the apiClient for invoice-related endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type {
  InvoiceFilters,
  InvoiceListResponse,
  InvoiceResponse,
} from '@/lib/types/invoice';

/**
 * Fetch a paginated, filtered list of invoices.
 *
 * Args:
 *   filters - Query parameters for filtering, sorting, and pagination.
 * Returns:
 *   Paginated invoice list with metadata.
 */
export async function fetchInvoices(
  filters: Partial<InvoiceFilters> = {},
): Promise<InvoiceListResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.set('page', String(filters.page));
  if (filters.per_page) params.set('per_page', String(filters.per_page));
  if (filters.status) params.set('status', filters.status);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.search) params.set('search', filters.search);
  if (filters.sort) params.set('sort', filters.sort);
  if (filters.order) params.set('order', filters.order);

  const query = params.toString();
  const endpoint = query ? `/api/v1/invoices?${query}` : '/api/v1/invoices';

  return apiClient<InvoiceListResponse>(endpoint);
}

/**
 * Delete an invoice by ID.
 *
 * Args:
 *   id - UUID of the invoice to delete.
 */
export async function deleteInvoice(id: string): Promise<void> {
  await apiClient<void>(`/api/v1/invoices/${id}`, { method: 'DELETE' });
}

/**
 * Mark an invoice as verified.
 *
 * Args:
 *   id - UUID of the invoice to verify.
 * Returns:
 *   Updated invoice with status "verified".
 */
export async function verifyInvoice(id: string): Promise<InvoiceResponse> {
  return apiClient<InvoiceResponse>(`/api/v1/invoices/${id}/verify`, {
    method: 'POST',
  });
}
