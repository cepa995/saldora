/**
 * Organization-related type definitions.
 */

export interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
  pib: string | null;
  billing_email: string | null;
  plan: string;
  settings: Record<string, unknown>;
}

export interface OrganizationUpdateRequest {
  name?: string;
  billing_email?: string | null;
  pib?: string | null;
  settings?: Record<string, unknown>;
}
