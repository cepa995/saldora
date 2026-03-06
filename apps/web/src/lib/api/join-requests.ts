/**
 * Join request API service functions.
 *
 * Typed wrappers around apiClient for join request endpoints.
 */

import { apiClient } from '@/lib/api-client';

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
