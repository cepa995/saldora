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
