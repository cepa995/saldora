/**
 * Modal for issuing a new paušal invoice.
 *
 * Supports picking an existing customer OR creating one inline, a
 * repeatable line-items list, dates, and place of issue. On submit
 * calls the issuance endpoint and surfaces the PDF URL in a success
 * toast.
 */

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  createCustomer,
  fetchCustomers,
  issueInvoice,
} from '@/lib/api/pausal';
import type {
  Customer,
  PausalInvoiceIssueRequest,
  PausalInvoiceItem,
  PausalInvoiceResponse,
} from '@/lib/types/pausal';
import type { ClientResponse } from '@/lib/types/client';
import { Toast } from '@/components/Toast';

interface Props {
  paušalac: ClientResponse;
  onClose: () => void;
  onIssued: (invoice: PausalInvoiceResponse) => void;
}

const DEFAULT_ITEM: PausalInvoiceItem = {
  description: '',
  quantity: '1',
  unit: 'kom',
  unit_price: '',
};

export function IssueInvoiceModal({ paušalac, onClose, onIssued }: Props) {
  const t = useTranslations('pausal');
  const tCommon = useTranslations('common');

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerMode, setCustomerMode] = useState<'existing' | 'new'>('existing');
  const [customerId, setCustomerId] = useState<string>('');
  const [newCustomerName, setNewCustomerName] = useState('');
  const [newCustomerPib, setNewCustomerPib] = useState('');

  const today = new Date().toISOString().slice(0, 10);
  const [invoiceDate, setInvoiceDate] = useState(today);
  const [dueDate, setDueDate] = useState('');
  const [placeOfIssue, setPlaceOfIssue] = useState(paušalac.city ?? 'Beograd');
  const [deliveryDate, setDeliveryDate] = useState('');
  const [deliveryPlace, setDeliveryPlace] = useState('');
  const [items, setItems] = useState<PausalInvoiceItem[]>([DEFAULT_ITEM]);
  const [notes, setNotes] = useState('');
  const [currency] = useState('RSD');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string } | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);

  const missingFields = useMemo(() => {
    const missing: string[] = [];
    if (!paušalac.bank_account) missing.push('bank_account');
    if (!paušalac.activity_code) missing.push('activity_code');
    return missing;
  }, [paušalac]);

  // Close on Escape
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [onClose]);

  // Lock body scroll while open
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  useEffect(() => {
    if (missingFields.length > 0) return;
    fetchCustomers(paušalac.id, { per_page: 100, is_active: true })
      .then((resp) => {
        setCustomers(resp.data);
        if (resp.data.length > 0) {
          setCustomerId(resp.data[0].id);
        } else {
          setCustomerMode('new');
        }
      })
      .catch(() => setCustomers([]));
  }, [paušalac.id, missingFields.length]);

  const subtotal = useMemo(() => {
    return items.reduce((sum, item) => {
      const q = Number(item.quantity) || 0;
      const p = Number(item.unit_price) || 0;
      return sum + q * p;
    }, 0);
  }, [items]);

  const fmtRsd = (n: number) =>
    new Intl.NumberFormat('sr-Latn-RS', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);

  function updateItem(idx: number, patch: Partial<PausalInvoiceItem>) {
    setItems((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (customerMode === 'existing' && !customerId) {
      setError(t('formSelectCustomer'));
      return;
    }
    if (customerMode === 'new' && !newCustomerName.trim()) {
      setError(t('formCustomerName'));
      return;
    }
    if (items.some((it) => !it.description || !it.unit_price || Number(it.unit_price) <= 0)) {
      setError(t('formItemDescription'));
      return;
    }

    setIsSubmitting(true);
    try {
      let effectiveCustomerId = customerId;

      // If using "new customer" mode, create first then issue so the
      // created customer persists even if issuance later fails.
      if (customerMode === 'new') {
        const created = await createCustomer(paušalac.id, {
          name: newCustomerName.trim(),
          pib: newCustomerPib.trim() || undefined,
        });
        effectiveCustomerId = created.id;
      }

      const payload: PausalInvoiceIssueRequest = {
        customer_id: effectiveCustomerId,
        invoice_date: invoiceDate,
        due_date: dueDate || null,
        place_of_issue: placeOfIssue,
        delivery_date: deliveryDate || null,
        delivery_place: deliveryPlace || null,
        items: items.map((it) => ({
          description: it.description,
          quantity: it.quantity,
          unit: it.unit || 'kom',
          unit_price: it.unit_price,
        })),
        currency,
        notes: notes.trim() || null,
      };

      const invoice = await issueInvoice(paušalac.id, payload);
      setToast({
        message: `${t('issuedSuccessTitle')} · ${t('issuedSuccessBody', { number: invoice.invoice_number })}`,
      });
      onIssued(invoice);
      setTimeout(onClose, 800);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : tCommon('error');
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start sm:items-center justify-center overflow-y-auto p-4 sm:p-6"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl my-4"
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{t('issueInvoiceTitle')}</h2>
            <p className="text-sm text-gray-500 mt-0.5">{t('issueInvoiceSubtitle')}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 -m-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
            aria-label={tCommon('close')}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Missing-fields gate */}
        {missingFields.length > 0 ? (
          <div className="p-6">
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-5">
              <h3 className="font-semibold text-amber-900 mb-1">
                {t('formMissingFieldsTitle')}
              </h3>
              <p className="text-sm text-amber-800">{t('formMissingFieldsBody')}</p>
              <ul className="mt-3 text-xs text-amber-700 font-mono list-disc list-inside">
                {missingFields.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                {tCommon('close')}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Customer */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-2">
                {t('formCustomer')}
              </h3>
              <div className="flex gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => setCustomerMode('existing')}
                  className={`flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    customerMode === 'existing'
                      ? 'bg-violet-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('formSelectCustomer')}
                </button>
                <button
                  type="button"
                  onClick={() => setCustomerMode('new')}
                  className={`flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    customerMode === 'new'
                      ? 'bg-violet-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {t('formNewCustomer')}
                </button>
              </div>
              {customerMode === 'existing' ? (
                <select
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
                >
                  {customers.length === 0 && <option value="">—</option>}
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                      {c.pib ? ` · PIB ${c.pib}` : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input
                    value={newCustomerName}
                    onChange={(e) => setNewCustomerName(e.target.value)}
                    placeholder={t('formCustomerName')}
                    className="px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                  <input
                    value={newCustomerPib}
                    onChange={(e) => setNewCustomerPib(e.target.value)}
                    placeholder={t('formCustomerPib')}
                    className="px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>
              )}
            </section>

            {/* Dates + place */}
            <section>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {t('formInvoiceDate')} <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={invoiceDate}
                    onChange={(e) => setInvoiceDate(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 box-border"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {t('formDueDate')}
                  </label>
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 box-border"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {t('formPlaceOfIssue')} <span className="text-rose-500">*</span>
                  </label>
                  <input
                    required
                    value={placeOfIssue}
                    onChange={(e) => setPlaceOfIssue(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {t('formDeliveryDate')}
                  </label>
                  <input
                    type="date"
                    value={deliveryDate}
                    onChange={(e) => setDeliveryDate(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 box-border"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {t('formDeliveryPlace')}
                  </label>
                  <input
                    value={deliveryPlace}
                    onChange={(e) => setDeliveryPlace(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>
              </div>
            </section>

            {/* Items */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-900">{t('formItems')}</h3>
                <button
                  type="button"
                  onClick={() => setItems((prev) => [...prev, { ...DEFAULT_ITEM }])}
                  className="text-xs font-semibold text-violet-700 hover:text-violet-900"
                >
                  + {t('formAddItem')}
                </button>
              </div>
              <div className="space-y-2">
                {items.map((item, idx) => {
                  const q = Number(item.quantity) || 0;
                  const p = Number(item.unit_price) || 0;
                  const lineTotal = q * p;
                  return (
                    <div
                      key={idx}
                      className="grid grid-cols-12 gap-2 items-start bg-gray-50 rounded-xl p-3"
                    >
                      <input
                        value={item.description}
                        onChange={(e) => updateItem(idx, { description: e.target.value })}
                        placeholder={t('formItemDescription')}
                        className="col-span-12 sm:col-span-5 px-2.5 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
                      />
                      <input
                        value={item.quantity}
                        onChange={(e) => updateItem(idx, { quantity: e.target.value })}
                        placeholder={t('formItemQuantity')}
                        type="number"
                        step="0.001"
                        min="0"
                        className="col-span-4 sm:col-span-2 px-2.5 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white tabular-nums"
                      />
                      <input
                        value={item.unit}
                        onChange={(e) => updateItem(idx, { unit: e.target.value })}
                        placeholder={t('formItemUnit')}
                        className="col-span-2 sm:col-span-1 px-2.5 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
                      />
                      <input
                        value={item.unit_price}
                        onChange={(e) => updateItem(idx, { unit_price: e.target.value })}
                        placeholder={t('formItemUnitPrice')}
                        type="number"
                        step="0.01"
                        min="0"
                        className="col-span-6 sm:col-span-2 px-2.5 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white tabular-nums"
                      />
                      <div className="col-span-5 sm:col-span-1 text-sm font-semibold text-gray-900 tabular-nums text-right py-2">
                        {fmtRsd(lineTotal)}
                      </div>
                      <button
                        type="button"
                        onClick={() => setItems((prev) => prev.filter((_, i) => i !== idx))}
                        className="col-span-1 text-gray-400 hover:text-rose-600 transition-colors justify-self-end p-1"
                        aria-label={t('formRemoveItem')}
                        disabled={items.length === 1}
                      >
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M10 3h4"
                          />
                        </svg>
                      </button>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center justify-end gap-3 mt-3 pt-3 border-t border-gray-100">
                <span className="text-sm text-gray-500">{t('total')}</span>
                <span className="text-xl font-bold text-gray-900 tabular-nums">
                  {fmtRsd(subtotal)} RSD
                </span>
              </div>
            </section>

            {/* Notes */}
            <section>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                {t('formNotes')}
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 resize-none"
              />
            </section>

            {error && (
              <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                {tCommon('cancel')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-violet-600 to-indigo-600 rounded-lg hover:from-violet-700 hover:to-indigo-700 shadow-sm shadow-violet-500/20 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSubmitting ? t('formSubmitting') : t('formSubmit')}
              </button>
            </div>
          </form>
        )}
      </div>

      {toast && (
        <Toast
          type="success"
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
