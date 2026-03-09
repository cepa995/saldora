/**
 * Join request API service functions.
 *
 * Typed wrappers around apiClient for join request endpoints.
 */

import { apiClient } from '@/lib/api-client';

export interface OrganizationSearchResult {
  id: string;
  name: string;
  slug: string;
}

/**
 * Search for organizations by name (public endpoint, min 3 chars).
 *
 * @param query - Search query string.
 * @returns Array of matching organizations.
 */
export async function searchOrganizations(query: string): Promise<OrganizationSearchResult[]> {
  return apiClient<OrganizationSearchResult[]>(
    `/api/v1/join-requests/organizations/search?q=${encodeURIComponent(query)}`,
    {},
    true,
  );
}

/**
 * Submit a join request to an organization.
 *
 * @param organizationId - Target organization UUID.
 * @param message - Optional message to the admin.
 * @returns Created join request.
 */
export async function submitJoinRequest(
  organizationId: string,
  message?: string,
): Promise<JoinRequestInfo> {
  return apiClient<JoinRequestInfo>('/api/v1/join-requests', {
    method: 'POST',
    body: JSON.stringify({ organization_id: organizationId, message: message || null }),
  });
}

export interface JoinRequestInfo {
  id: string;
  organization_id: string;
  user_id: string;
  message: string | null;
  status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  user_email: string | null;
  user_name: string | null;
  organization_name: string | null;
}

/**
 * Get the current user's pending join request, if any.
 *
 * @returns Pending join request or null.
 */
export async function getMyPendingRequest(): Promise<JoinRequestInfo | null> {
  return apiClient<JoinRequestInfo | null>('/api/v1/join-requests/mine');
}

/**
 * List pending join requests for the organization (admin only).
 *
 * @returns Array of pending join requests.
 */
export async function fetchJoinRequests(): Promise<JoinRequestInfo[]> {
  return apiClient<JoinRequestInfo[]>('/api/v1/join-requests');
}

/**
 * Approve a join request (admin only).
 *
 * @param requestId - UUID of the join request.
 * @returns Success message.
 */
export async function approveJoinRequest(requestId: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/api/v1/join-requests/${requestId}/approve`, {
    method: 'POST',
  });
}

/**
 * Reject a join request (admin only).
 *
 * @param requestId - UUID of the join request.
 * @returns Success message.
 */
export async function rejectJoinRequest(requestId: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/api/v1/join-requests/${requestId}/reject`, {
    method: 'POST',
  });
}

/**
 * Get the count of pending join requests for the organization (admin only).
 *
 * @returns Object with count of pending requests.
 */
export async function getPendingJoinRequestCount(): Promise<{ count: number }> {
  return apiClient<{ count: number }>('/api/v1/join-requests/pending-count');
}
