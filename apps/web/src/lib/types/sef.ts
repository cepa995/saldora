/**
 * TypeScript interfaces for SEF (Sistem Elektronskih Faktura) inbox.
 *
 * These types define the structure for incoming eFaktura invoices
 * received from the Serbian electronic invoicing system.
 */

export type SefStatus =
  | "new"
  | "pending"
  | "processed"
  | "rejected"
  | "archived";

export interface SefInvoice {
  id: string;
  sef_id: string;
  status: SefStatus;
  invoice_number: string | null;
  supplier_name: string | null;
  supplier_pib: string | null;
  amount: string | null;
  currency: string;
  invoice_date: string | null;
  received_at: string;
  processed_invoice_id: string | null;
  created_at: string;
  updated_at: string;
}

export type SefSortColumn =
  | "received_at"
  | "amount"
  | "status"
  | "invoice_date";

export type SortOrder = "asc" | "desc";

export interface SefFilters {
  page: number;
  per_page: number;
  status?: SefStatus;
  date_from?: string;
  date_to?: string;
  search?: string;
  sort: SefSortColumn;
  order: SortOrder;
}

export interface SefPaginationInfo {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface SefListResponse {
  data: SefInvoice[];
  pagination: SefPaginationInfo;
}

export interface SefSyncStatus {
  last_sync_at: string | null;
  pending_count: number;
  is_syncing: boolean;
}
