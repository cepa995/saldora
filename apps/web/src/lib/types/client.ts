/**
 * TypeScript interfaces mirroring backend client schemas.
 */

export interface ClientSummary {
  id: string;
  name: string;
  pib: string;
}

export interface ClientResponse {
  id: string;
  organization_id: string;
  name: string;
  pib: string;
  mb: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  is_active: boolean;
  notes: string | null;
  invoice_count: number;
  total_amount: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientCreate {
  name: string;
  pib: string;
  mb?: string;
  address?: string;
  city?: string;
  postal_code?: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
}

export interface ClientUpdate {
  name?: string;
  pib?: string;
  mb?: string | null;
  address?: string | null;
  city?: string | null;
  postal_code?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
  is_active?: boolean;
}

export interface ClientListResponse {
  data: ClientResponse[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}
