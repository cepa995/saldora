/**
 * Client API service functions.
 *
 * Typed wrappers around the apiClient for client-related endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type {
  ClientCreate,
  ClientListResponse,
  ClientResponse,
  ClientUpdate,
} from '@/lib/types/client';

/**
 * Fetch a paginated, filtered list of clients.
 *
 * Args:
 *   filters - Query parameters for filtering and pagination.
 * Returns:
 *   Paginated client list with metadata.
 */
export async function fetchClients(
  filters: {
    search?: string;
    is_active?: boolean;
    page?: number;
    per_page?: number;
  } = {},
): Promise<ClientListResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.set('page', String(filters.page));
  if (filters.per_page) params.set('per_page', String(filters.per_page));
  if (filters.search) params.set('search', filters.search);
  if (filters.is_active !== undefined)
    params.set('is_active', String(filters.is_active));

  // Canonical backend URL has a trailing slash; hitting it directly avoids a
  // 307 redirect that in some browsers drops the Authorization header.
  const query = params.toString();
  const endpoint = query ? `/api/v1/clients/?${query}` : '/api/v1/clients/';

  return apiClient<ClientListResponse>(endpoint);
}

/**
 * Fetch a single client by id.
 */
export async function fetchClient(id: string): Promise<ClientResponse> {
  return apiClient<ClientResponse>(`/api/v1/clients/${id}`);
}

export interface ClientWorkspaceStats {
  invoice_count: number;
  pending_count: number;
  blocked_count: number;
  total_amount: number;
}

interface CountResp {
  pagination: { total: number };
  data: { total_amount: string | null }[];
}

/**
 * Compute per-period stats for a client by probing the invoice list endpoint.
 *
 * Uses three parallel counted queries (pending / blocked / all). Avoids a
 * dedicated stats endpoint; fine for a single client where result sets are
 * small. Upgrade to a backend aggregation if the workspace ever paints more
 * than these three tiles.
 */
export async function fetchClientWorkspaceStats(
  clientId: string,
  period: string,
): Promise<ClientWorkspaceStats> {
  const [y, m] = period.split('-').map(Number);
  const from = `${y}-${String(m).padStart(2, '0')}-01`;
  const lastDay = new Date(y, m, 0).getDate();
  const to = `${y}-${String(m).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;

  const base = `client_id=${encodeURIComponent(clientId)}&date_from=${from}&date_to=${to}`;
  // Backend caps per_page at 100. Summing total_amount across the first 100 invoices
  // covers every client we target (a café/bar rarely exceeds that in a single month).
  // If we ever need exact totals for heavier clients, move this to a backend aggregate.
  const [all, pending, blocked] = await Promise.all([
    apiClient<CountResp>(`/api/v1/invoices?${base}&per_page=100`),
    apiClient<CountResp>(`/api/v1/invoices?${base}&status=review&per_page=1`),
    apiClient<CountResp>(`/api/v1/invoices?${base}&status=error&per_page=1`),
  ]);

  const totalAmount = all.data.reduce(
    (acc, row) => acc + Number(row.total_amount ?? 0),
    0,
  );

  return {
    invoice_count: all.pagination.total,
    pending_count: pending.pagination.total,
    blocked_count: blocked.pagination.total,
    total_amount: totalAmount,
  };
}

export interface ClientEventResponse {
  id: string;
  organization_id: string;
  client_id: string | null;
  event_type: string;
  event_date: string;
  payload: Record<string, unknown>;
  entity_type: string | null;
  entity_id: string | null;
  actor_user_id: string | null;
  created_at: string;
}

export interface ClientEventListResponse {
  data: ClientEventResponse[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

/**
 * Fetch the client's event stream (Timeline data).
 */
export async function fetchClientEvents(
  clientId: string,
  params: { period?: string; event_type?: string; page?: number; per_page?: number } = {},
): Promise<ClientEventListResponse> {
  const qs = new URLSearchParams();
  if (params.period) qs.set('period', params.period);
  if (params.event_type) qs.set('event_type', params.event_type);
  if (params.page) qs.set('page', String(params.page));
  if (params.per_page) qs.set('per_page', String(params.per_page));
  const query = qs.toString();
  const url = `/api/v1/clients/${clientId}/events${query ? `?${query}` : ''}`;
  return apiClient<ClientEventListResponse>(url);
}

/**
 * Create a new client.
 *
 * Args:
 *   data - Client creation data.
 * Returns:
 *   Created client response.
 */
export async function createClient(
  data: ClientCreate,
): Promise<ClientResponse> {
  return apiClient<ClientResponse>('/api/v1/clients/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing client.
 *
 * Args:
 *   id - UUID of the client to update.
 *   data - Partial update data.
 * Returns:
 *   Updated client response.
 */
export async function updateClient(
  id: string,
  data: ClientUpdate,
): Promise<ClientResponse> {
  return apiClient<ClientResponse>(`/api/v1/clients/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Deactivate (soft-delete) a client.
 *
 * Args:
 *   id - UUID of the client to deactivate.
 */
export async function deleteClient(id: string): Promise<void> {
  await apiClient<void>(`/api/v1/clients/${id}`, { method: 'DELETE' });
}

/**
 * Toggle client active/inactive status.
 */
export async function toggleClientActive(id: string): Promise<{ is_active: boolean }> {
  return apiClient<{ is_active: boolean }>(`/api/v1/clients/${id}/toggle-active`, { method: 'POST' });
}
