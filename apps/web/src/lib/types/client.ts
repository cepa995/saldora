/**
 * TypeScript interfaces mirroring backend client schemas.
 */

export type LegalForm = 'DOO' | 'preduzetnik' | 'paušalac' | 'drugo';
export type BookkeepingSystem = 'dvojno' | 'prosto';

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
  legal_form: LegalForm | null;
  bookkeeping_system: BookkeepingSystem | null;
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
  legal_form?: LegalForm;
  bookkeeping_system?: BookkeepingSystem;
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
  legal_form?: LegalForm | null;
  bookkeeping_system?: BookkeepingSystem | null;
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

/** Per-form status returned by GET /api/v1/clients/{id}/obligations.
 * Mirrors `app.services.hospitality_forms.FormStatus`. */
export type ObligationFormStatus =
  | 'shipped'
  | 'pre_meeting'
  | 'post_meeting'
  | 'not_applicable'
  | 'unclassified';

/** Form keys returned by the obligations endpoint. Mirrors
 * `app.services.hospitality_forms.FormKey`. */
export type ObligationFormKey =
  | 'kalkulacija'
  | 'kep'
  | 'cenovnik'
  | 'popis'
  | 'dpu'
  | 'pk1';

export interface ClientObligationsResponse {
  legal_form: LegalForm | null;
  bookkeeping_system: BookkeepingSystem | null;
  forms: Record<ObligationFormKey, ObligationFormStatus>;
}
