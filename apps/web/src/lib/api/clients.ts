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

  const query = params.toString();
  const endpoint = query ? `/api/v1/clients?${query}` : '/api/v1/clients';

  return apiClient<ClientListResponse>(endpoint);
}

/**
 * Fetch a single client by id.
 */
export async function fetchClient(id: string): Promise<ClientResponse> {
  return apiClient<ClientResponse>(`/api/v1/clients/${id}`);
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
  return apiClient<ClientResponse>('/api/v1/clients', {
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
