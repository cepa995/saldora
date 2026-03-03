/**
 * SEF (eFaktura) inbox API service functions.
 *
 * Typed wrappers around the apiClient for SEF-related endpoints.
 * Backend endpoints will be implemented in M7 (SEF Integration).
 */

import { apiClient } from "@/lib/api-client";
import type {
  SefFilters,
  SefListResponse,
  SefInvoice,
  SefSyncStatus,
} from "@/lib/types/sef";

/**
 * Fetch a paginated, filtered list of SEF inbox invoices.
 *
 * Args:
 *   filters - Query parameters for filtering, sorting, and pagination.
 * Returns:
 *   Paginated SEF invoice list with metadata.
 */
export async function fetchSefInbox(
  filters: Partial<SefFilters> = {},
): Promise<SefListResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));
  if (filters.status) params.set("status", filters.status);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.search) params.set("search", filters.search);
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.order) params.set("order", filters.order);

  const query = params.toString();
  const endpoint = query ? `/api/v1/sef/inbox?${query}` : "/api/v1/sef/inbox";

  return apiClient<SefListResponse>(endpoint);
}

/**
 * Fetch a single SEF invoice by ID.
 *
 * Args:
 *   id - UUID of the SEF invoice.
 * Returns:
 *   Full SEF invoice response.
 */
export async function fetchSefInvoice(id: string): Promise<SefInvoice> {
  return apiClient<SefInvoice>(`/api/v1/sef/inbox/${id}`);
}

/**
 * Process a SEF invoice — creates a FakturaAI invoice from it.
 *
 * Args:
 *   id - UUID of the SEF invoice to process.
 * Returns:
 *   Updated SEF invoice with status "processed".
 */
export async function processSefInvoice(id: string): Promise<SefInvoice> {
  return apiClient<SefInvoice>(`/api/v1/sef/inbox/${id}/process`, {
    method: "POST",
  });
}

/**
 * Reject a SEF invoice.
 *
 * Args:
 *   id - UUID of the SEF invoice to reject.
 * Returns:
 *   Updated SEF invoice with status "rejected".
 */
export async function rejectSefInvoice(id: string): Promise<SefInvoice> {
  return apiClient<SefInvoice>(`/api/v1/sef/inbox/${id}/reject`, {
    method: "POST",
  });
}

/**
 * Archive a SEF invoice.
 *
 * Args:
 *   id - UUID of the SEF invoice to archive.
 * Returns:
 *   Updated SEF invoice with status "archived".
 */
export async function archiveSefInvoice(id: string): Promise<SefInvoice> {
  return apiClient<SefInvoice>(`/api/v1/sef/inbox/${id}/archive`, {
    method: "POST",
  });
}

/**
 * Trigger a manual sync with the SEF system.
 *
 * Returns:
 *   Updated sync status.
 */
export async function triggerSefSync(): Promise<SefSyncStatus> {
  return apiClient<SefSyncStatus>("/api/v1/sef/sync", {
    method: "POST",
  });
}

/**
 * Fetch current SEF sync status.
 *
 * Returns:
 *   Sync status including last sync time and pending count.
 */
export async function fetchSefSyncStatus(): Promise<SefSyncStatus> {
  return apiClient<SefSyncStatus>("/api/v1/sef/sync/status");
}
