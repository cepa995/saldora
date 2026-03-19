/**
 * ZZPL compliance API service functions.
 *
 * Typed wrappers for consent, deletion requests, and privacy policy endpoints.
 */

import { apiClient } from '@/lib/api-client';

export interface ConsentStatus {
  consent_type: string;
  granted: boolean;
  granted_at: string | null;
  revoked_at: string | null;
}

export interface ConsentRecord {
  id: string;
  consent_type: string;
  granted: boolean;
  granted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface DeletionRequest {
  id: string;
  status: string;
  request_type: string;
  retained_categories: Record<string, string> | null;
  created_at: string;
}

export interface PrivacyPolicy {
  version: string;
  effective_date: string;
  content: string;
}

/**
 * Fetch current consent status for all types.
 *
 * @returns List of consent statuses.
 */
export async function fetchConsentStatus(): Promise<ConsentStatus[]> {
  return apiClient<ConsentStatus[]>('/api/v1/compliance/consent');
}

/**
 * Grant consent for a specific type.
 *
 * @param consentType - Type of consent to grant.
 * @param version - Optional consent text version.
 * @returns Created consent record.
 */
export async function grantConsent(
  consentType: string,
  version?: string,
): Promise<ConsentRecord> {
  return apiClient<ConsentRecord>('/api/v1/compliance/consent', {
    method: 'POST',
    body: JSON.stringify({
      consent_type: consentType,
      consent_text_version: version ?? null,
    }),
  });
}

/**
 * Revoke consent for a specific type.
 *
 * @param consentType - Type of consent to revoke.
 * @returns Confirmation message.
 */
export async function revokeConsent(
  consentType: string,
): Promise<{ message: string }> {
  return apiClient<{ message: string }>('/api/v1/compliance/consent/revoke', {
    method: 'POST',
    body: JSON.stringify({ consent_type: consentType }),
  });
}

/**
 * Submit a data deletion request.
 *
 * @returns Created deletion request.
 */
export async function createDeletionRequest(): Promise<DeletionRequest> {
  return apiClient<DeletionRequest>('/api/v1/compliance/deletion-requests', {
    method: 'POST',
    body: JSON.stringify({ request_type: 'user_only' }),
  });
}

/**
 * Fetch the public privacy policy.
 *
 * @returns Privacy policy content.
 */
export async function fetchPrivacyPolicy(): Promise<PrivacyPolicy> {
  return apiClient<PrivacyPolicy>(
    '/api/v1/compliance/privacy-policy',
    {},
    true,
  );
}
