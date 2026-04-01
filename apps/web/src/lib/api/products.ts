/**
 * Product Catalog API service functions.
 *
 * Typed wrappers around apiClient for product catalog endpoints.
 */

import { apiClient } from '@/lib/api-client';

// ── Types ────────────────────────────────────────────────────────────

export interface Product {
  id: string;
  organization_id: string;
  canonical_name: string;
  unit_of_measure: string | null;
  category: string | null;
  aliases: string[];
  selling_price: number | null;
  default_margin_pct: number | null;
  match_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  canonical_name: string;
  unit_of_measure?: string;
  category?: string;
  aliases?: string[];
  selling_price?: number;
  default_margin_pct?: number;
}

export interface MergeSuggestion {
  description_a: string;
  description_b: string;
  similarity: number;
  supplier_a: string | null;
  supplier_b: string | null;
  suggested_canonical: string;
}

// ── Functions ────────────────────────────────────────────────────────

/**
 * Fetch all products for the current organization.
 *
 * @param category - Optional category filter.
 * @param search - Optional name search filter.
 * @returns List of products.
 */
export async function fetchProducts(category?: string, search?: string): Promise<Product[]> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (search) params.set('search', search);
  const qs = params.toString();
  return apiClient<Product[]>(`/api/v1/products/${qs ? '?' + qs : ''}`);
}

/**
 * Create a new product.
 *
 * @param data - Product creation payload.
 * @returns Created product.
 */
export async function createProduct(data: ProductCreate): Promise<Product> {
  return apiClient<Product>('/api/v1/products/', { method: 'POST', body: JSON.stringify(data) });
}

/**
 * Update an existing product.
 *
 * @param id - Product ID.
 * @param data - Partial product update payload.
 * @returns Updated product.
 */
export async function updateProduct(id: string, data: Partial<ProductCreate>): Promise<Product> {
  return apiClient<Product>(`/api/v1/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

/**
 * Delete a product.
 *
 * @param id - Product ID.
 */
export async function deleteProduct(id: string): Promise<void> {
  await apiClient(`/api/v1/products/${id}`, { method: 'DELETE' });
}

/**
 * Fetch merge suggestions for similar product names.
 *
 * @param threshold - Similarity threshold (0-1).
 * @returns Merge suggestions with total count.
 */
export async function fetchMergeSuggestions(threshold?: number): Promise<{ suggestions: MergeSuggestion[]; total: number }> {
  const qs = threshold ? `?threshold=${threshold}` : '';
  return apiClient(`/api/v1/products/suggestions/merge${qs}`);
}

/**
 * Merge multiple product descriptions into a canonical product.
 *
 * @param canonicalName - The canonical name to use.
 * @param descriptions - List of descriptions to merge.
 * @param category - Optional category.
 * @param unitOfMeasure - Optional unit of measure.
 * @returns Merged product.
 */
export async function mergeProducts(
  canonicalName: string,
  descriptions: string[],
  category?: string,
  unitOfMeasure?: string,
): Promise<Product> {
  const params = new URLSearchParams();
  params.set('canonical_name', canonicalName);
  descriptions.forEach((d) => params.append('descriptions', d));
  if (category) params.set('category', category);
  if (unitOfMeasure) params.set('unit_of_measure', unitOfMeasure);
  return apiClient<Product>(`/api/v1/products/merge?${params.toString()}`, { method: 'POST' });
}
