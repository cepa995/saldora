import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useInvoiceList } from '@/hooks/useInvoiceList';
import type { InvoiceListResponse, InvoiceResponse } from '@/lib/types/invoice';

const mockInvoice = (overrides: Partial<InvoiceResponse> = {}): InvoiceResponse => ({
  id: 'inv-1',
  status: 'review',
  confidence_score: 85,
  invoice_number: 'INV-001',
  invoice_date: '2026-01-15',
  due_date: '2026-02-15',
  seller: { pib: '123456789', mb: null, name: 'Firma DOO', address: 'Adresa 1', city: null, postal_code: null, verified: true, apr_status: null },
  buyer: { pib: '987654321', mb: null, name: 'Kupac DOO', address: 'Adresa 2', city: null, postal_code: null, verified: false, apr_status: null },
  subtotal: '10000',
  tax_rate: '20',
  tax_amount: '2000',
  total_amount: '12000',
  currency: 'RSD',
  line_items: [],
  field_confidences: [],
  warnings: [],
  blocked: false,
  field_warnings: {},
  document_url: null,
  raw_ocr_text: null,
  raw_llm_output: null,
  created_at: '2026-01-15T10:00:00Z',
  updated_at: '2026-01-15T10:00:00Z',
  ...overrides,
});

const mockListResponse: InvoiceListResponse = {
  data: [mockInvoice(), mockInvoice({ id: 'inv-2', invoice_number: 'INV-002' })],
  pagination: { page: 1, per_page: 20, total: 2, total_pages: 1 },
};

vi.mock('@/lib/api/invoices', () => ({
  fetchInvoices: vi.fn(),
  deleteInvoice: vi.fn(),
  verifyInvoice: vi.fn(),
}));

import { fetchInvoices, deleteInvoice, verifyInvoice } from '@/lib/api/invoices';

const mockFetchInvoices = vi.mocked(fetchInvoices);
const mockDeleteInvoice = vi.mocked(deleteInvoice);
const mockVerifyInvoice = vi.mocked(verifyInvoice);

describe('useInvoiceList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchInvoices.mockResolvedValue(mockListResponse);
    mockDeleteInvoice.mockResolvedValue(undefined);
    mockVerifyInvoice.mockResolvedValue(mockInvoice({ status: 'verified' }));
  });

  it('loads invoices on mount', async () => {
    const { result } = renderHook(() => useInvoiceList());
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.invoices).toHaveLength(2);
    expect(result.current.pagination.total).toBe(2);
    expect(mockFetchInvoices).toHaveBeenCalled();
  });

  it('sets error on fetch failure', async () => {
    mockFetchInvoices.mockRejectedValueOnce(new Error('Network error'));
    const { result } = renderHook(() => useInvoiceList());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeTruthy();
  });

  it('filters by status and resets page to 1', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setStatus('review'));

    await waitFor(() => expect(result.current.filters.status).toBe('review'));
    expect(result.current.filters.page).toBe(1);
  });

  it('toggles sort order when clicking same column', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setSort('invoice_date'));
    expect(result.current.filters.sort).toBe('invoice_date');
    expect(result.current.filters.order).toBe('asc');

    act(() => result.current.setSort('invoice_date'));
    expect(result.current.filters.order).toBe('desc');
  });

  it('resets to asc when switching to a different sort column', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setSort('total_amount'));
    expect(result.current.filters.sort).toBe('total_amount');
    expect(result.current.filters.order).toBe('asc');
  });

  it('toggles individual selection', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.toggleSelect('inv-1'));
    expect(result.current.selectedIds.has('inv-1')).toBe(true);

    act(() => result.current.toggleSelect('inv-1'));
    expect(result.current.selectedIds.has('inv-1')).toBe(false);
  });

  it('toggles select all', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.toggleSelectAll());
    expect(result.current.selectedIds.size).toBe(2);

    act(() => result.current.toggleSelectAll());
    expect(result.current.selectedIds.size).toBe(0);
  });

  it('clears selection', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.toggleSelect('inv-1'));
    act(() => result.current.clearSelection());
    expect(result.current.selectedIds.size).toBe(0);
  });

  it('sets page number', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setPage(3));
    expect(result.current.filters.page).toBe(3);
  });

  it('sets date range', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setDateRange('2026-01-01', '2026-01-31'));
    expect(result.current.filters.date_from).toBe('2026-01-01');
    expect(result.current.filters.date_to).toBe('2026-01-31');
  });

  it('batch verifies selected invoices', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.toggleSelect('inv-1'));
    act(() => result.current.toggleSelect('inv-2'));

    await act(async () => {
      await result.current.batchVerify();
    });

    expect(mockVerifyInvoice).toHaveBeenCalledTimes(2);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it('batch deletes selected invoices', async () => {
    const { result } = renderHook(() => useInvoiceList());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.toggleSelect('inv-1'));

    await act(async () => {
      await result.current.batchDelete();
    });

    expect(mockDeleteInvoice).toHaveBeenCalledWith('inv-1');
    expect(result.current.selectedIds.size).toBe(0);
  });
});
