/**
 * Invitation API service functions.
 *
 * Typed wrappers around apiClient for invitation endpoints.
 */

import { apiClient } from '@/lib/api-client';

export interface InvitationInfo {
  id: string;
  email: string;
  role: string;
  status: string;
  token: string;
  invited_by: string;
  organization_id: string;
  expires_at: string;
  created_at: string;
}

export interface CreateInvitationRequest {
  email: string;
  role: string;
}

/**
 * Create a new invitation.
 *
 * @param data - Email and role for the invitation.
 * @returns Created invitation with token.
 */
export async function createInvitation(data: CreateInvitationRequest): Promise<InvitationInfo> {
  return apiClient<InvitationInfo>('/api/v1/invitations', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * List pending invitations for the organization.
 *
 * @returns Array of pending invitations.
 */
export async function fetchInvitations(): Promise<InvitationInfo[]> {
  return apiClient<InvitationInfo[]>('/api/v1/invitations');
}

/**
 * Revoke a pending invitation.
 *
 * @param invitationId - UUID of the invitation.
 * @returns Success message.
 */
export async function revokeInvitation(invitationId: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/api/v1/invitations/${invitationId}`, {
    method: 'DELETE',
  });
}
