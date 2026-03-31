'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useClient } from '@/contexts/ClientContext';
import { fetchClients, createClient, updateClient, deleteClient } from '@/lib/api/clients';
import { isPlanError } from '@/lib/api-client';
import { UpgradeModal, type PlanErrorInfo } from '@/components/UpgradeModal';
import type { ClientResponse, ClientCreate, ClientUpdate } from '@/lib/types/client';

export default function ClientsPage() {
  const t = useTranslations('clients');
  const tc = useTranslations('common');
  const { hasRole } = useAuth();
  const { refresh: refreshContext } = useClient();

  const [clients, setClients] = useState<ClientResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientResponse | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);

  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Debounce search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [search]);

  const loadClients = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchClients({
        search: debouncedSearch || undefined,
        page,
        per_page: 20,
      });
      setClients(result.data);
      setTotalPages(result.pagination.total_pages);
      setTotal(result.pagination.total);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setError(t('loadError'));
      }
    } finally {
      setIsLoading(false);
    }
  }, [debouncedSearch, page, t]);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  // Auto-clear toast
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  async function handleSave(data: ClientCreate | ClientUpdate) {
    setSaving(true);
    try {
      if (editingClient) {
        await updateClient(editingClient.id, data as ClientUpdate);
        setToast({ message: t('editSuccess'), type: 'success' });
      } else {
        await createClient(data as ClientCreate);
        setToast({ message: t('createSuccess'), type: 'success' });
      }
      setModalOpen(false);
      setEditingClient(null);
      loadClients();
      refreshContext();
    } catch (err: unknown) {
      const apiErr = err as { status?: number; message?: string };
      if (apiErr?.status === 409) {
        setToast({ message: t('duplicatePib'), type: 'error' });
      } else {
        setToast({ message: t('saveError'), type: 'error' });
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteClient(id);
      setToast({ message: t('deleteSuccess'), type: 'success' });
      setDeleteConfirm(null);
      loadClients();
      refreshContext();
    } catch {
      setToast({ message: t('deleteError'), type: 'error' });
    }
  }

  if (planError) {
    return <UpgradeModal error={planError} onClose={() => window.history.back()} />;
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
          {total > 0 && (
            <p className="text-sm text-gray-500 mt-1">
              {total} {total === 1 ? t('clientSingular') : t('clientPlural')}
            </p>
          )}
        </div>
        {hasRole('manager') && (
          <button
            onClick={() => {
              setEditingClient(null);
              setModalOpen(true);
            }}
            className="px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 transition-colors"
          >
            {t('addClient')}
          </button>
        )}
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('searchPlaceholder')}
          className="w-full max-w-md px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg">{error}</div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
        </div>
      ) : clients.length === 0 ? (
        /* Empty state */
        <div className="text-center py-20">
          <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <p className="text-gray-500 text-lg font-medium">{t('emptyState')}</p>
          <p className="text-gray-400 text-sm mt-1">{t('emptyStateSubtitle')}</p>
        </div>
      ) : (
        /* Client cards grid */
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clients.map((client) => (
              <div
                key={client.id}
                className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-base font-semibold text-gray-900 truncate">{client.name}</h3>
                    <p className="text-sm text-gray-500">{t('pib')}: {client.pib}</p>
                  </div>
                  {!client.is_active && (
                    <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-full">
                      {t('inactive')}
                    </span>
                  )}
                </div>

                {(client.city || client.address) && (
                  <p className="text-sm text-gray-500 mb-2 truncate">
                    {[client.address, client.city].filter(Boolean).join(', ')}
                  </p>
                )}

                <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                  <span>{t('invoiceCount')}: {client.invoice_count}</span>
                  {client.total_amount && (
                    <span className="font-medium text-gray-700">
                      {Number(client.total_amount).toLocaleString('sr-Latn-RS')} RSD
                    </span>
                  )}
                </div>

                {hasRole('manager') && (
                  <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                    <button
                      onClick={() => {
                        setEditingClient(client);
                        setModalOpen(true);
                      }}
                      className="px-3 py-1.5 text-sm text-violet-600 hover:bg-violet-50 rounded-lg transition-colors"
                    >
                      {tc('edit')}
                    </button>
                    {client.is_active ? (
                      <button
                        onClick={() => setDeleteConfirm(client.id)}
                        className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        {tc('delete')}
                      </button>
                    ) : (
                      <button
                        onClick={async () => {
                          try {
                            const { reactivateClient } = await import('@/lib/api/clients');
                            await reactivateClient(client.id);
                            loadClients();
                          } catch { /* ignore */ }
                        }}
                        className="px-3 py-1.5 text-sm text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                      >
                        Aktiviraj
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                {tc('previous')}
              </button>
              <span className="text-sm text-gray-500">
                {tc('page')} {page} {tc('of')} {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                {tc('next')}
              </button>
            </div>
          )}
        </>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <ClientModal
          client={editingClient}
          saving={saving}
          onSave={handleSave}
          onClose={() => {
            setModalOpen(false);
            setEditingClient(null);
          }}
        />
      )}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('deleteConfirmTitle')}</h3>
            <p className="text-sm text-gray-600 mb-4">{t('deleteConfirmMessage')}</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                {tc('cancel')}
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                {tc('delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}

/** Modal form for creating/editing a client. */
function ClientModal({
  client,
  saving,
  onSave,
  onClose,
}: {
  client: ClientResponse | null;
  saving: boolean;
  onSave: (data: ClientCreate | ClientUpdate) => void;
  onClose: () => void;
}) {
  const t = useTranslations('clients');
  const tc = useTranslations('common');

  const [name, setName] = useState(client?.name || '');
  const [pib, setPib] = useState(client?.pib || '');
  const [mb, setMb] = useState(client?.mb || '');
  const [address, setAddress] = useState(client?.address || '');
  const [city, setCity] = useState(client?.city || '');
  const [postalCode, setPostalCode] = useState(client?.postal_code || '');
  const [email, setEmail] = useState(client?.contact_email || '');
  const [phone, setPhone] = useState(client?.contact_phone || '');
  const [notes, setNotes] = useState(client?.notes || '');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data: ClientCreate | ClientUpdate = {
      name,
      pib,
      mb: mb || undefined,
      address: address || undefined,
      city: city || undefined,
      postal_code: postalCode || undefined,
      contact_email: email || undefined,
      contact_phone: phone || undefined,
      notes: notes || undefined,
    };
    onSave(data);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {client ? t('editClient') : t('createClient')}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('name')} *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('pib')} *</label>
              <input
                type="text"
                value={pib}
                onChange={(e) => setPib(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('mb')}</label>
              <input
                type="text"
                value={mb}
                onChange={(e) => setMb(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('address')}</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('city')}</label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('postalCode')}</label>
              <input
                type="text"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('contactEmail')}</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('contactPhone')}</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('notes')}</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 resize-none"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              {tc('cancel')}
            </button>
            <button
              type="submit"
              disabled={saving || !name || !pib}
              className="px-4 py-2 text-sm bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? tc('saving') : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
