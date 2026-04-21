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
  convertToRsd,
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
import { validateSerbianPib } from '@/lib/validation/pib';

// Curated, commonly-used countries for paušalci. RS first, then the usual
// destinations (US, UK, EU), then a long tail users can still type via ISO.
const COUNTRIES: Array<{ code: string; label: string }> = [
  { code: 'RS', label: '🇷🇸 Srbija' },
  { code: 'US', label: '🇺🇸 SAD' },
  { code: 'GB', label: '🇬🇧 Ujedinjeno Kraljevstvo' },
  { code: 'DE', label: '🇩🇪 Nemačka' },
  { code: 'AT', label: '🇦🇹 Austrija' },
  { code: 'CH', label: '🇨🇭 Švajcarska' },
  { code: 'IT', label: '🇮🇹 Italija' },
  { code: 'FR', label: '🇫🇷 Francuska' },
  { code: 'NL', label: '🇳🇱 Holandija' },
  { code: 'IE', label: '🇮🇪 Irska' },
  { code: 'HR', label: '🇭🇷 Hrvatska' },
  { code: 'SI', label: '🇸🇮 Slovenija' },
  { code: 'ME', label: '🇲🇪 Crna Gora' },
  { code: 'BA', label: '🇧🇦 BiH' },
  { code: 'MK', label: '🇲🇰 S. Makedonija' },
  { code: 'BG', label: '🇧🇬 Bugarska' },
  { code: 'HU', label: '🇭🇺 Mađarska' },
  { code: 'OTHER', label: '🌍 Ostalo' },
];

// Subset of NBS-supported currencies. Keep in sync with the backend's
// SUPPORTED_CURRENCIES in pausal_invoice_issuance.py.
const CURRENCIES = ['RSD', 'EUR', 'USD', 'CHF', 'GBP'] as const;

// Country → currency default used when the user first picks the country.
// The user can still override.
const COUNTRY_CURRENCY_HINT: Record<string, string> = {
  RS: 'RSD',
  US: 'USD',
  GB: 'GBP',
  CH: 'CHF',
  // All eurozone / EU presets → EUR
  DE: 'EUR',
  AT: 'EUR',
  IT: 'EUR',
  FR: 'EUR',
  NL: 'EUR',
  IE: 'EUR',
  HR: 'EUR',
  SI: 'EUR',
  ME: 'EUR',
  BG: 'EUR',
  // Non-euro neighbours left unset → keep user's last choice
};

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
  const [newCustomerCountry, setNewCustomerCountry] = useState<string>('RS');
  const [newCustomerPibTouched, setNewCustomerPibTouched] = useState(false);

  const isSerbianCustomer = newCustomerCountry === 'RS';
  const newCustomerPibValidation = isSerbianCustomer
    ? validateSerbianPib(newCustomerPib)
    : { valid: true, error: null };
  const newCustomerPibError =
    isSerbianCustomer && newCustomerPibTouched && newCustomerPib.length > 0
      ? newCustomerPibValidation.error
      : null;

  const today = new Date().toISOString().slice(0, 10);
  const [invoiceDate, setInvoiceDate] = useState(today);
  const [dueDate, setDueDate] = useState('');
  const [placeOfIssue, setPlaceOfIssue] = useState(paušalac.city ?? 'Beograd');
  const [deliveryDate, setDeliveryDate] = useState('');
  const [deliveryPlace, setDeliveryPlace] = useState('');
  const [items, setItems] = useState<PausalInvoiceItem[]>([DEFAULT_ITEM]);
  const [notes, setNotes] = useState('');
  const [currency, setCurrency] = useState<string>('RSD');
  const [rsdEquivalent, setRsdEquivalent] = useState<{
    amount: string;
    rate: string;
    rateDate: string;
  } | null>(null);

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

  // Live NBS conversion hint for non-RSD invoices — debounced.
  useEffect(() => {
    if (currency === 'RSD') {
      setRsdEquivalent(null);
      return;
    }
    const total = items.reduce((sum, item) => {
      const q = Number(item.quantity) || 0;
      const p = Number(item.unit_price) || 0;
      return sum + q * p;
    }, 0);
    if (total <= 0 || !invoiceDate) {
      setRsdEquivalent(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      void convertToRsd(String(total), currency, invoiceDate).then((result) => {
        if (cancelled || !result || !result.rsd_amount) return;
        const formatted = new Intl.NumberFormat('sr-Latn-RS', {
          maximumFractionDigits: 0,
        }).format(Math.round(Number(result.rsd_amount)));
        setRsdEquivalent({
          amount: formatted,
          rate: result.exchange_rate ?? '',
          rateDate: result.rate_date ?? invoiceDate,
        });
      });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [currency, invoiceDate, items]);

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
    if (customerMode === 'new' && !newCustomerPibValidation.valid) {
      setNewCustomerPibTouched(true);
      setError(newCustomerPibValidation.error);
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
        const resolvedCountry =
          newCustomerCountry === 'OTHER' ? 'XX' : newCustomerCountry;
        const created = await createCustomer(paušalac.id, {
          name: newCustomerName.trim(),
          pib: newCustomerPib.trim() || undefined,
          country: resolvedCountry,
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
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-stretch sm:items-center justify-center p-0 sm:p-6"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        className="bg-white w-full sm:rounded-2xl shadow-2xl sm:max-w-5xl flex flex-col max-h-full sm:max-h-[92vh] overflow-hidden"
      >
        {/* Sticky header */}
        <div className="flex items-start justify-between px-5 sm:px-6 py-4 sm:py-5 border-b border-gray-100 flex-shrink-0">
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
          <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
            <div className="overflow-y-auto px-5 sm:px-6 py-5 flex-1">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 lg:gap-6">
            {/* ——— Left column ——— */}
            <div className="space-y-5">
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
                <div className="space-y-3">
                  <input
                    value={newCustomerName}
                    onChange={(e) => setNewCustomerName(e.target.value)}
                    placeholder={t('formCustomerName')}
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        {t('formCustomerCountry')}
                      </label>
                      <select
                        value={newCustomerCountry}
                        onChange={(e) => {
                          const nextCountry = e.target.value;
                          setNewCustomerCountry(nextCountry);
                          setNewCustomerPibTouched(false);
                          // Auto-suggest a currency based on the country.
                          const hint = COUNTRY_CURRENCY_HINT[nextCountry];
                          if (hint) setCurrency(hint);
                        }}
                        className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 bg-white"
                      >
                        {COUNTRIES.map((c) => (
                          <option key={c.code} value={c.code}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        {isSerbianCustomer
                          ? t('formCustomerPib')
                          : t('formCustomerForeignTaxId')}
                      </label>
                      <input
                        value={newCustomerPib}
                        onChange={(e) =>
                          setNewCustomerPib(
                            isSerbianCustomer
                              ? e.target.value.replace(/\D/g, '').slice(0, 9)
                              : e.target.value.slice(0, 30),
                          )
                        }
                        onBlur={() => setNewCustomerPibTouched(true)}
                        placeholder={isSerbianCustomer ? '123456789' : 'EIN / VAT ID'}
                        inputMode={isSerbianCustomer ? 'numeric' : 'text'}
                        className={`w-full px-3 py-2.5 text-sm border rounded-lg focus:ring-2 tabular-nums ${
                          newCustomerPibError
                            ? 'border-rose-300 focus:ring-rose-500/20 focus:border-rose-400'
                            : 'border-gray-200 focus:ring-violet-500/20 focus:border-violet-500'
                        }`}
                      />
                      {newCustomerPibError && (
                        <p className="mt-1 text-xs text-rose-600">{newCustomerPibError}</p>
                      )}
                      {!isSerbianCustomer && (
                        <p className="mt-1 text-xs text-gray-500">
                          {t('formCustomerForeignTaxIdHint')}
                        </p>
                      )}
                    </div>
                  </div>
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
            </div>
            {/* ——— Right column ——— */}
            <div className="space-y-5">

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
              <div className="mt-3 pt-3 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500">{t('formCurrency')}</label>
                  <select
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="px-2 py-1 text-xs font-semibold border border-gray-200 rounded-md bg-white focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 tabular-nums"
                  >
                    {CURRENCIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-sm text-gray-500">{t('total')}</span>
                  <span className="text-xl font-bold text-gray-900 tabular-nums">
                    {fmtRsd(subtotal)} {currency}
                  </span>
                </div>
              </div>
              {currency !== 'RSD' && rsdEquivalent && (
                <div className="mt-1 text-right text-xs text-gray-500">
                  ≈ <span className="font-medium text-gray-700">{rsdEquivalent.amount} RSD</span>{' '}
                  <span className="text-gray-400">
                    ({t('formNbsRateAt', { date: rsdEquivalent.rateDate })})
                  </span>
                </div>
              )}
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
            </div>
              </div>

              {error && (
                <div className="mt-5 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}
            </div>

            {/* Sticky footer */}
            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 px-5 sm:px-6 py-4 border-t border-gray-100 bg-white flex-shrink-0">
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
