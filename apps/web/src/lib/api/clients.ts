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
