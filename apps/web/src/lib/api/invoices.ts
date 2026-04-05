/**
 * Invoice API service functions.
 *
 * Typed wrappers around the apiClient for invoice-related endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type {
  AccountingIntentResponse,
  AccountingIntentUpdateRequest,
  InvoiceFilters,
  InvoiceListResponse,
  InvoiceResponse,
  InvoiceUpdate,
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
  if (filters.accounting_review !== undefined)
    params.set('accounting_review', String(filters.accounting_review));
  if (filters.book_type) params.set('book_type', filters.book_type);
  if (filters.payment_status) params.set('payment_status', filters.payment_status);
  if (filters.client_id) params.set('client_id', filters.client_id);

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

/**
 * Fetch a single invoice by ID.
 *
 * Args:
 *   id - UUID of the invoice.
 * Returns:
 *   Full invoice response.
 */
export async function fetchInvoice(id: string): Promise<InvoiceResponse> {
  return apiClient<InvoiceResponse>(`/api/v1/invoices/${id}`);
}

/**
 * Update an invoice (partial update).
 *
 * Args:
 *   id - UUID of the invoice.
 *   data - Fields to update.
 * Returns:
 *   Updated invoice response.
 */
export async function updateInvoice(
  id: string,
  data: InvoiceUpdate,
): Promise<InvoiceResponse> {
  return apiClient<InvoiceResponse>(`/api/v1/invoices/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Assign or unassign a client to an invoice.
 *
 * Args:
 *   invoiceId - UUID of the invoice.
 *   clientId - UUID of the client, or null to unassign.
 * Returns:
 *   Updated invoice response.
 */
export async function assignClientToInvoice(
  invoiceId: string,
  clientId: string | null,
): Promise<InvoiceResponse> {
  const params = clientId ? `?client_id=${clientId}` : '';
  return apiClient<InvoiceResponse>(
    `/api/v1/invoices/${invoiceId}/client${params}`,
    { method: 'PATCH' },
  );
}

/**
 * Fetch accounting intent for a verified invoice.
 *
 * Args:
 *   invoiceId - UUID of the invoice.
 * Returns:
 *   Accounting intent or null if not yet generated.
 */
/**
 * Get queue information (depth, your pending, estimated wait).
 */
export async function fetchQueueInfo(): Promise<{
  queue_depth: number;
  your_pending: number;
  estimated_minutes: number;
  workers: number;
}> {
  return apiClient('/api/v1/invoices/queue/info');
}

export async function fetchAccountingIntent(
  invoiceId: string,
): Promise<AccountingIntentResponse | null> {
  try {
    return await apiClient<AccountingIntentResponse>(
      `/api/v1/invoices/${invoiceId}/accounting-intent`,
    );
  } catch {
    return null;
  }
}

/**
 * Mark an accounting intent as reviewed.
 *
 * Args:
 *   invoiceId - UUID of the invoice.
 *   notes - Optional reviewer notes.
 * Returns:
 *   Updated accounting intent.
 */
/**
 * Update accounting intent fields (konta, classification, notes).
 *
 * Args:
 *   invoiceId - UUID of the invoice.
 *   data - Fields to update.
 * Returns:
 *   Updated accounting intent.
 */
export async function updateAccountingIntent(
  invoiceId: string,
  data: AccountingIntentUpdateRequest,
): Promise<AccountingIntentResponse> {
  return apiClient<AccountingIntentResponse>(
    `/api/v1/invoices/${invoiceId}/accounting-intent`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
  );
}

export async function reviewAccountingIntent(
  invoiceId: string,
  notes?: string,
): Promise<AccountingIntentResponse> {
  return apiClient<AccountingIntentResponse>(
    `/api/v1/invoices/${invoiceId}/accounting-intent/review`,
    {
      method: 'POST',
      body: JSON.stringify({ notes: notes ?? null }),
    },
  );
}

/**
 * Record a payment against an invoice.
 */
export async function recordPayment(
  invoiceId: string,
  data: { amount: number; payment_date?: string; notes?: string },
): Promise<InvoiceResponse> {
  return apiClient<InvoiceResponse>(
    `/api/v1/invoices/${invoiceId}/payment`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
  );
}

/**
 * Batch mark invoices as fully paid.
 */
export async function batchMarkAsPaid(
  invoiceIds: string[],
): Promise<{ updated: number; skipped: number; skipped_ids: string[] }> {
  return apiClient<{ updated: number; skipped: number; skipped_ids: string[] }>(
    '/api/v1/invoices/batch-payment',
    {
      method: 'POST',
      body: JSON.stringify({ invoice_ids: invoiceIds }),
    },
  );
}
