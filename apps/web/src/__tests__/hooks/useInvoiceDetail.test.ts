import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useInvoiceDetail } from '@/hooks/useInvoiceDetail';
import type { InvoiceResponse } from '@/lib/types/invoice';

const mockInvoice: InvoiceResponse = {
  id: 'inv-1',
  status: 'review',
  confidence_score: 90,
  invoice_number: 'INV-001',
  invoice_date: '2026-01-15',
  due_date: '2026-02-15',
  seller: { pib: '123456789', name: 'Firma DOO', address: 'Adresa 1', city: null, postal_code: null, verified: true, apr_status: null },
  buyer: { pib: '987654321', name: 'Kupac DOO', address: 'Adresa 2', city: null, postal_code: null, verified: false, apr_status: null },
  subtotal: '10000',
  tax_rate: '20',
  tax_amount: '2000',
  total_amount: '12000',
  currency: 'RSD',
  line_items: [],
  field_confidences: [
    { field_name: 'invoice_number', value: 'INV-001', confidence: 95, needs_review: false },
  ],
  warnings: [],
  blocked: false,
  document_url: 'https://example.com/doc.pdf',
  created_at: '2026-01-15T10:00:00Z',
  updated_at: '2026-01-15T10:00:00Z',
};

vi.mock('@/lib/api/invoices', () => ({
  fetchInvoice: vi.fn(),
  updateInvoice: vi.fn(),
  deleteInvoice: vi.fn(),
  verifyInvoice: vi.fn(),
}));

import { fetchInvoice, updateInvoice, deleteInvoice, verifyInvoice } from '@/lib/api/invoices';

const mockFetchInvoice = vi.mocked(fetchInvoice);
const mockUpdateInvoice = vi.mocked(updateInvoice);
const mockDeleteInvoice = vi.mocked(deleteInvoice);
const mockVerifyInvoice = vi.mocked(verifyInvoice);

describe('useInvoiceDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchInvoice.mockResolvedValue(mockInvoice);
    mockUpdateInvoice.mockResolvedValue({ ...mockInvoice, invoice_number: 'INV-002' });
    mockVerifyInvoice.mockResolvedValue({ ...mockInvoice, status: 'verified' });
    mockDeleteInvoice.mockResolvedValue(undefined);
  });

  it('loads invoice on mount', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.invoice).toBeTruthy();
    expect(result.current.invoice?.invoice_number).toBe('INV-001');
    expect(mockFetchInvoice).toHaveBeenCalledWith('inv-1');
  });

  it('sets error on fetch failure', async () => {
    mockFetchInvoice.mockRejectedValueOnce(new Error('Not found'));
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.invoice).toBeNull();
  });

  it('tracks field edits and hasChanges', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.hasChanges).toBe(false);

    act(() => result.current.setField('invoice_number', 'INV-002'));

    expect(result.current.hasChanges).toBe(true);
    expect(result.current.editedFields.invoice_number).toBe('INV-002');
  });

  it('saves edited fields', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setField('invoice_number', 'INV-002'));

    let success = false;
    await act(async () => {
      success = await result.current.save();
    });

    expect(success).toBe(true);
    expect(mockUpdateInvoice).toHaveBeenCalledWith('inv-1', { invoice_number: 'INV-002' });
    expect(result.current.hasChanges).toBe(false);
  });

  it('returns true on save with no changes', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let success = false;
    await act(async () => {
      success = await result.current.save();
    });

    expect(success).toBe(true);
    expect(mockUpdateInvoice).not.toHaveBeenCalled();
  });

  it('verifies the invoice', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let success = false;
    await act(async () => {
      success = await result.current.verify();
    });

    expect(success).toBe(true);
    expect(mockVerifyInvoice).toHaveBeenCalledWith('inv-1');
    expect(result.current.invoice?.status).toBe('verified');
  });

  it('deletes the invoice', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let success = false;
    await act(async () => {
      success = await result.current.remove();
    });

    expect(success).toBe(true);
    expect(mockDeleteInvoice).toHaveBeenCalledWith('inv-1');
  });

  it('discards changes', async () => {
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setField('invoice_number', 'CHANGED'));
    expect(result.current.hasChanges).toBe(true);

    act(() => result.current.discardChanges());
    expect(result.current.hasChanges).toBe(false);
    expect(result.current.editedFields).toEqual({});
  });

  it('handles save failure', async () => {
    mockUpdateInvoice.mockRejectedValueOnce(new Error('Server error'));
    const { result } = renderHook(() => useInvoiceDetail('inv-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => result.current.setField('invoice_number', 'CHANGED'));

    let success = true;
    await act(async () => {
      success = await result.current.save();
    });

    expect(success).toBe(false);
    expect(result.current.error).toBeTruthy();
  });
});
