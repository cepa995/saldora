/**
 * User profile API service functions.
 *
 * Typed wrappers around apiClient for user profile endpoints.
 */

import { apiClient } from '@/lib/api-client';

export interface UserProfile {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  email_verified: boolean;
  organization_id: string;
  created_at: string;
}

export interface UpdateProfileRequest {
  first_name?: string;
  last_name?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/**
 * Fetch the current user's profile.
 *
 * @returns User profile details.
 */
export async function fetchProfile(): Promise<UserProfile> {
  return apiClient<UserProfile>('/api/v1/users/me');
}

/**
 * Update the current user's profile.
 *
 * @param data - Fields to update (first_name, last_name).
 * @returns Updated user profile.
 */
export async function updateProfile(data: UpdateProfileRequest): Promise<UserProfile> {
  return apiClient<UserProfile>('/api/v1/users/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Change the current user's password.
 *
 * @param data - Current and new password.
 * @returns Success message.
 */
export async function changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
  return apiClient<{ message: string }>('/api/v1/users/me/change-password', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
