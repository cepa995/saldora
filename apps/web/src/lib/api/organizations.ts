/**
 * Organization API service functions.
 *
 * Typed wrappers around apiClient for organization endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type { OrganizationInfo, OrganizationUpdateRequest } from '@/lib/types/organization';

/**
 * Fetch the current user's organization details.
 *
 * @returns Organization info including name, slug, billing email, and settings.
 */
export async function fetchOrganization(): Promise<OrganizationInfo> {
  return apiClient<OrganizationInfo>('/api/v1/organizations/current');
}

/**
 * Update the current organization's settings.
 *
 * @param data - Fields to update (name, billing_email, pib, settings).
 * @returns Updated organization info.
 */
export async function updateOrganization(data: OrganizationUpdateRequest): Promise<OrganizationInfo> {
  return apiClient<OrganizationInfo>('/api/v1/organizations/current', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Upload an organization logo.
 *
 * @param file - Image file (PNG or JPG, max 2 MB).
 * @returns Object with the presigned logo URL.
 */
export async function uploadLogo(file: File): Promise<{ logo_url: string }> {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient<{ logo_url: string }>('/api/v1/organizations/current/logo', {
    method: 'POST',
    body: formData,
    // Don't set Content-Type header — browser sets it with boundary for FormData
  });
}

/**
 * Delete the organization logo.
 *
 * @returns Success message.
 */
export async function deleteLogo(): Promise<{ message: string }> {
  return apiClient<{ message: string }>('/api/v1/organizations/current/logo', {
    method: 'DELETE',
  });
}
