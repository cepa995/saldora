/**
 * Team management API service functions.
 *
 * Typed wrappers around apiClient for team member endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type { TeamMember } from '@/lib/types/team';

/**
 * List all members of the current organization.
 *
 * @returns Array of team members.
 */
export async function fetchTeamMembers(): Promise<TeamMember[]> {
  return apiClient<TeamMember[]>('/api/v1/team/members');
}

/**
 * Update a team member's role.
 *
 * @param userId - UUID of the member.
 * @param role - New role to assign.
 * @returns Updated team member.
 */
export async function updateMemberRole(userId: string, role: string): Promise<TeamMember> {
  return apiClient<TeamMember>(`/api/v1/team/members/${userId}/role`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
}

/**
 * Remove a member from the organization.
 *
 * @param userId - UUID of the member to remove.
 * @returns Success message.
 */
export async function removeMember(userId: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/api/v1/team/members/${userId}`, {
    method: 'DELETE',
  });
}
