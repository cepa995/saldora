/**
 * TypeScript interfaces mirroring backend client schemas.
 */

export type ClientType =
  | 'vat_payer'
  | 'pausalac'
  | 'foreign_entity'
  | 'non_profit';

export interface ClientSummary {
  id: string;
  name: string;
  pib: string;
  client_type?: ClientType;
}

export interface ClientResponse {
  id: string;
  organization_id: string;
  name: string;
  pib: string;
  mb: string | null;
  client_type: ClientType;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  is_active: boolean;
  notes: string | null;
  bank_account: string | null;
  activity_code: string | null;
  invoice_count: number;
  total_amount: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientCreate {
  name: string;
  pib: string;
  mb?: string;
  client_type?: ClientType;
  address?: string;
  city?: string;
  postal_code?: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
  bank_account?: string;
  activity_code?: string;
}

export interface ClientUpdate {
  name?: string;
  pib?: string;
  mb?: string | null;
  client_type?: ClientType;
  address?: string | null;
  city?: string | null;
  postal_code?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  notes?: string | null;
  is_active?: boolean;
  bank_account?: string | null;
  activity_code?: string | null;
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
