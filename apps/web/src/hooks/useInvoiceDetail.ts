'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import {
  fetchInvoice,
  updateInvoice,
  deleteInvoice,
  verifyInvoice,
} from '@/lib/api/invoices';
import type { InvoiceResponse, InvoiceUpdate } from '@/lib/types/invoice';

interface UseInvoiceDetailReturn {
  invoice: InvoiceResponse | null;
  isLoading: boolean;
  error: string | null;
  isSaving: boolean;
  isVerifying: boolean;
  isDeleting: boolean;
  editedFields: Partial<InvoiceUpdate>;
  hasChanges: boolean;
  setField: (field: keyof InvoiceUpdate, value: string) => void;
  save: () => Promise<boolean>;
  verify: () => Promise<boolean>;
  remove: () => Promise<boolean>;
  discardChanges: () => void;
  refresh: () => void;
}

/**
 * Manages invoice detail state, editing, saving, verification, and deletion.
 */
export function useInvoiceDetail(id: string): UseInvoiceDetailReturn {
  const router = useRouter();
  const { user } = useAuth();
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editedFields, setEditedFields] = useState<Partial<InvoiceUpdate>>({});

  const hasChanges = Object.keys(editedFields).length > 0;

  const loadInvoice = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchInvoice(id);
      setInvoice(result);
    } catch {
      setError('Greška pri učitavanju fakture');
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadInvoice();
  }, [loadInvoice]);

  const setField = useCallback(
    (field: keyof InvoiceUpdate, value: string) => {
      setEditedFields((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const save = useCallback(async (): Promise<boolean> => {
    if (!hasChanges) return true;
    setIsSaving(true);
    try {
      const updated = await updateInvoice(id, editedFields);
      setInvoice(updated);
      setEditedFields({});
      return true;
    } catch {
      setError('Greška pri čuvanju izmena');
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [id, editedFields, hasChanges]);

  const verify = useCallback(async (): Promise<boolean> => {
    setIsVerifying(true);
    try {
      const updated = await verifyInvoice(id);
      setInvoice(updated);
      setEditedFields({});
      return true;
    } catch (err: unknown) {
      const apiErr = err as { message?: string; status?: number; detail?: string };
      const msg = apiErr?.detail || apiErr?.message || '';
      if (apiErr?.status === 409) {
        setError(msg || 'Duplikat fakture — faktura sa istim brojem već postoji');
      } else if (apiErr?.status === 400 && msg.includes("'verified'")) {
        setError('Faktura je već verifikovana');
      } else if (apiErr?.status === 400 && msg.includes('status')) {
        setError('Faktura nije u statusu za verifikaciju');
      } else {
        setError(msg || 'Greška pri verifikaciji fakture');
      }
      return false;
    } finally {
      setIsVerifying(false);
    }
  }, [id]);

  const remove = useCallback(async (): Promise<boolean> => {
    setIsDeleting(true);
    try {
      await deleteInvoice(id);
      router.push(user?.orgSlug ? `/${user.orgSlug}/invoices` : '/invoices');
      return true;
    } catch {
      setError('Greška pri brisanju fakture');
      return false;
    } finally {
      setIsDeleting(false);
    }
  }, [id, router, user?.orgSlug]);

  const discardChanges = useCallback(() => {
    setEditedFields({});
  }, []);

  const refresh = useCallback(() => {
    setEditedFields({});
    loadInvoice();
  }, [loadInvoice]);

  return {
    invoice,
    isLoading,
    error,
    isSaving,
    isVerifying,
    isDeleting,
    editedFields,
    hasChanges,
    setField,
    save,
    verify,
    remove,
    discardChanges,
    refresh,
  };
}
