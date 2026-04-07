'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { use } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useClient } from '@/contexts/ClientContext';
import { useOrgPath } from '@/lib/navigation';
import { useInvoiceDetail } from '@/hooks/useInvoiceDetail';
import { StatusBadge } from '@/components/StatusBadge';
import { ConfidenceBadge } from '@/components/ConfidenceBadge';
import { DocumentViewer } from '@/components/DocumentViewer';
import { EditableField } from '@/components/EditableField';
import { Toast, type ToastType } from '@/components/Toast';
import { ExportDialog } from '@/components/ExportDialog';
import { formatAmountSr } from '@/lib/formatters';
import { assignClientToInvoice, fetchAccountingIntent, reviewAccountingIntent, updateAccountingIntent } from '@/lib/api/invoices';
import type { InvoiceUpdate, FieldConfidence, LineItem, TaxGroup, AccountingIntentResponse, KontoEntry } from '@/lib/types/invoice';

const CURRENCIES = ['RSD', 'EUR', 'USD', 'BAM', 'HRK', 'CHF', 'GBP'];

export default function InvoiceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { hasRole } = useAuth();
  const { isAgency, clients } = useClient();
  const orgPath = useOrgPath();
  const t = useTranslations('detail');
  const tCommon = useTranslations('common');
  const canWrite = hasRole('operator');
  const canDelete = hasRole('manager');
  const {
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
  } = useInvoiceDetail(id);
  const [isAssigningClient, setIsAssigningClient] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);
  const [accountingIntent, setAccountingIntent] = useState<AccountingIntentResponse | null>(null);
  const [isReviewingIntent, setIsReviewingIntent] = useState(false);
  const [editingKonta, setEditingKonta] = useState(false);
  const [editedDebit, setEditedDebit] = useState<KontoEntry[]>([]);
  const [editedCredit, setEditedCredit] = useState<KontoEntry[]>([]);
  const [isSavingKonta, setIsSavingKonta] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);

  const isProcessing = invoice?.status === 'processing' || !canWrite;
  const canVerify = invoice?.status === 'review';

  // Load accounting intent for verified invoices
  useEffect(() => {
    if (invoice?.status === 'verified' || invoice?.status === 'exported') {
      fetchAccountingIntent(id).then(setAccountingIntent);
    }
  }, [id, invoice?.status]);

  // Close more menu on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (moreMenuRef.current && !moreMenuRef.current.contains(e.target as Node)) {
        setShowMoreMenu(false);
      }
    }
    if (showMoreMenu) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showMoreMenu]);

  // Ctrl+S to save
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (hasChanges && !isSaving) handleSave();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  });

  function toggleSection(section: string) {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) next.delete(section);
      else next.add(section);
      return next;
    });
  }

  function getConfidence(fieldName: string): number | null {
    if (!invoice?.field_confidences) return null;
    const fc = invoice.field_confidences.find(
      (f: FieldConfidence) => f.field_name === fieldName,
    );
    return fc?.confidence ?? null;
  }

  function getFieldValue(field: keyof InvoiceUpdate, original: string | null | undefined): string | null {
    if (field in editedFields) return (editedFields[field] as string) ?? null;
    return original ?? null;
  }

  function isDirty(field: keyof InvoiceUpdate): boolean {
    return field in editedFields;
  }

  function getFieldWarning(field: string): 'error' | 'warning' | undefined {
    if (!invoice?.field_warnings) return undefined;
    return invoice.field_warnings[field];
  }

  function resetField(field: keyof InvoiceUpdate) {
    // Remove from editedFields by creating a new object without this field
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { [field]: _, ...rest } = editedFields;
    // We need to use the hook's setField to clear it — but the hook only adds.
    // Instead, discard all and re-set the remaining edits.
    discardChanges();
    Object.entries(rest).forEach(([k, v]) => {
      setField(k as keyof InvoiceUpdate, v as string);
    });
  }

  const handleSave = useCallback(async () => {
    const ok = await save();
    if (ok) setToast({ message: t('saveSuccess'), type: 'success' });
  }, [save, t]);

  const handleVerify = useCallback(async () => {
    const ok = await verify();
    if (ok) {
      setToast({ message: t('verifySuccess'), type: 'success' });
      fetchAccountingIntent(id).then(setAccountingIntent);
    } else if (error) {
      setToast({ message: error, type: 'error' });
    }
  }, [verify, t, id, error]);

  const handleReviewIntent = useCallback(async () => {
    setIsReviewingIntent(true);
    try {
      const updated = await reviewAccountingIntent(id);
      setAccountingIntent(updated);
      setToast({ message: t('intentReviewSuccess'), type: 'success' });
    } catch {
      setToast({ message: t('intentReviewError'), type: 'error' });
    } finally {
      setIsReviewingIntent(false);
    }
  }, [id, t]);

  const handleClientAssign = useCallback(async (clientId: string | null) => {
    setIsAssigningClient(true);
    try {
      await assignClientToInvoice(id, clientId);
      refresh();
      setToast({
        message: clientId ? t('clientAssigned') : t('clientUnassigned'),
        type: 'success',
      });
    } catch {
      setToast({ message: t('clientAssignError'), type: 'error' });
    } finally {
      setIsAssigningClient(false);
    }
  }, [id, refresh, t]);

  const handleDelete = useCallback(async () => {
    setShowDeleteConfirm(false);
    await remove();
    // remove() redirects, so no toast needed
  }, [remove]);

  // Computed total check
  const computedTotal = (() => {
    if (!invoice) return null;
    const sub = parseFloat(getFieldValue('subtotal', invoice.subtotal) ?? '');
    const tax = parseFloat(getFieldValue('tax_amount', invoice.tax_amount) ?? '');
    if (isNaN(sub) || isNaN(tax)) return null;
    return sub + tax;
  })();

  const actualTotal = parseFloat(getFieldValue('total_amount', invoice?.total_amount) ?? '');

  // Line items editing
  function getLineItems(): LineItem[] {
    if (editedFields.line_items) return editedFields.line_items;
    return invoice?.line_items ?? [];
  }

  function setLineItem(index: number, field: keyof LineItem, value: string) {
    const items = [...getLineItems()];
    items[index] = { ...items[index], [field]: value };
    setField('line_items', items as unknown as string);
  }

  function addLineItem() {
    const items = [...getLineItems(), { description: '', quantity: '1', unit_price: '0', total: '0', tax_rate: null, tax_amount: null }];
    setField('line_items', items as unknown as string);
  }

  function removeLineItem(index: number) {
    const items = getLineItems().filter((_, i) => i !== index);
    setField('line_items', items as unknown as string);
  }

  // Tax groups editing
  function getTaxGroups(): TaxGroup[] {
    if (editedFields.tax_groups) return editedFields.tax_groups as unknown as TaxGroup[];
    return invoice?.tax_groups ?? [];
  }

  function setTaxGroup(index: number, field: keyof TaxGroup, value: string) {
    const groups = [...getTaxGroups()];
    groups[index] = { ...groups[index], [field]: value };
    setField('tax_groups', groups as unknown as string);
  }

  function addTaxGroup() {
    const groups = [...getTaxGroups(), { rate: '20', base_amount: '0', tax_amount: '0' }];
    setField('tax_groups', groups as unknown as string);
  }

  function removeTaxGroup(index: number) {
    const groups = getTaxGroups().filter((_, i) => i !== index);
    setField('tax_groups', groups as unknown as string);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-violet-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-gray-400">{tCommon('loading')}</span>
        </div>
      </div>
    );
  }

  if (error && !invoice) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-gray-500 mb-4">{error}</p>
        <Link href={orgPath("/invoices")} className="text-sm font-medium text-violet-600 hover:text-violet-700">
          {t('backToList')}
        </Link>
      </div>
    );
  }

  if (!invoice) return null;

  return (
    <div className="space-y-4">
      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Top bar */}
      <div className="space-y-3">
        {/* Back link */}
        <Link
          href={orgPath("/invoices")}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors w-full justify-center sm:justify-start sm:w-auto"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          {t('backToList')}
        </Link>

        {/* Title row: invoice number + status + confidence + actions */}
        <div className="flex items-center justify-center sm:justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <h1 className="text-lg font-semibold text-gray-900 truncate">
              {invoice.invoice_number || '#\u2014'}
            </h1>
            <StatusBadge status={invoice.status} />
            {(invoice.status === 'verified' || invoice.status === 'exported') && (
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                invoice.payment_status === 'paid'
                  ? 'bg-green-50 text-green-700 ring-1 ring-green-600/20'
                  : invoice.payment_status === 'partially_paid'
                  ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20'
                  : 'bg-gray-100 text-gray-600'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  invoice.payment_status === 'paid' ? 'bg-green-500'
                    : invoice.payment_status === 'partially_paid' ? 'bg-amber-500'
                    : 'bg-gray-400'
                }`} />
                {invoice.payment_status === 'paid' ? t('paid')
                  : invoice.payment_status === 'partially_paid' ? t('partiallyPaid')
                  : t('unpaid')}
              </span>
            )}
            {invoice.confidence_score !== null && (
              <>
                <div className="hidden sm:block w-px h-5 bg-gray-200" />
                <div className="hidden sm:flex items-center gap-1.5">
                  <span className="text-xs text-gray-400">{t('confidence')}</span>
                  <ConfidenceBadge confidence={invoice.confidence_score} />
                </div>
              </>
            )}
          </div>

          {/* Client selector — desktop (Agency only) */}
          {isAgency && canWrite && (
            <select
              value={invoice.client_id ?? ''}
              onChange={(e) => handleClientAssign(e.target.value || null)}
              disabled={isAssigningClient || isProcessing}
              className="hidden sm:block text-sm border border-gray-200 rounded-xl px-3 py-1.5 bg-white text-gray-700 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent disabled:opacity-50 max-w-[200px] truncate"
            >
              <option value="">{t('noClient')}</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.pib})
                </option>
              ))}
            </select>
          )}

          <div className="flex items-center gap-2 shrink-0">
            {canWrite && canVerify && (
              <button
                onClick={handleVerify}
                disabled={isVerifying}
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-xl hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {isVerifying ? t('verifying') : t('verify')}
              </button>
            )}
            {canWrite && hasChanges && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 disabled:opacity-50 transition-colors"
              >
                {isSaving ? tCommon('saving') : t('saveChanges')}
              </button>
            )}
            {(invoice.status === 'verified' || invoice.status === 'exported') && invoice.payment_status !== 'paid' && (
              <button
                onClick={() => setShowPaymentModal(true)}
                className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-xl hover:bg-emerald-700 transition-colors inline-flex items-center gap-1.5"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z" />
                </svg>
                <span className="hidden sm:inline">{t('recordPayment')}</span>
              </button>
            )}
            {/* More actions menu */}
            <div className="relative" ref={moreMenuRef}>
              <button
                onClick={() => setShowMoreMenu(!showMoreMenu)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                title={t('moreActions')}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                </svg>
              </button>
              {showMoreMenu && (
                <div className="absolute right-0 mt-1 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-20">
                  <button
                    onClick={() => {
                      setShowMoreMenu(false);
                      setShowExportDialog(true);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    {tCommon('export')}
                  </button>
                  {canDelete && (
                    <button
                      onClick={() => {
                        setShowMoreMenu(false);
                        setShowDeleteConfirm(true);
                      }}
                      disabled={isDeleting}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
                    >
                      {isDeleting ? tCommon('deleting') : t('deleteInvoice')}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Confidence badge - mobile only (shown below title) */}
        {invoice.confidence_score !== null && (
          <div className="sm:hidden flex items-center justify-center gap-1.5">
            <span className="text-xs text-gray-400">{t('confidence')}</span>
            <ConfidenceBadge confidence={invoice.confidence_score} />
          </div>
        )}

        {/* Client selector — mobile (Agency only) */}
        {isAgency && canWrite && (
          <select
            value={invoice.client_id ?? ''}
            onChange={(e) => handleClientAssign(e.target.value || null)}
            disabled={isAssigningClient || isProcessing}
            className="sm:hidden w-full text-sm border border-gray-200 rounded-xl px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent disabled:opacity-50"
          >
            <option value="">{t('noClient')}</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.pib})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Warnings */}
      {invoice.warnings.length > 0 && (
        <div className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${
          invoice.blocked
            ? 'bg-red-50 border-red-100'
            : 'bg-amber-50 border-amber-100'
        }`}>
          <svg className={`w-5 h-5 shrink-0 mt-0.5 ${invoice.blocked ? 'text-red-500' : 'text-amber-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <div>
            {invoice.blocked && (
              <p className="text-sm font-medium text-red-700 mb-1">{t('blocked')}</p>
            )}
            <ul className="space-y-0.5">
              {invoice.warnings.map((warning, i) => (
                <li key={i} className={`text-sm ${invoice.blocked ? 'text-red-600' : 'text-amber-700'}`}>
                  {warning}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Processing progress */}
      {isProcessing && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-violet-100 bg-violet-50">
          <svg className="animate-spin h-5 w-5 text-violet-600 shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm font-medium text-violet-700">{t('processingStage')}</span>
        </div>
      )}

      {/* Main content: document + form */}
      <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100dvh-9rem)] lg:min-h-[500px]">
        {/* Document viewer */}
        <div className="lg:w-1/2 h-[50vh] lg:h-full bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <DocumentViewer url={invoice.document_url} />
        </div>

        {/* Data form */}
        <div className="lg:w-1/2 space-y-4 lg:overflow-y-auto lg:pb-16">
          {/* Accounting intent (shown after verification) */}
          {accountingIntent && (
            <FieldGroup
              title={t('accountingIntent')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              }
              collapsed={collapsedSections.has('accountingIntent')}
              onToggle={() => toggleSection('accountingIntent')}
            >
              <div className="space-y-4">
                {/* Classification badges */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="bg-gray-50 rounded-xl p-3">
                    <div className="text-xs text-gray-500 mb-1">{t('documentType')}</div>
                    <div className="text-sm font-medium text-gray-900">
                      {t(`doctype_${accountingIntent.document_type}` as Parameters<typeof t>[0])}
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <div className="text-xs text-gray-500 mb-1">{t('transactionType')}</div>
                    <div className="text-sm font-medium text-gray-900">
                      {t(`txntype_${accountingIntent.transaction_type}` as Parameters<typeof t>[0])}
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <div className="text-xs text-gray-500 mb-1">{t('vatTreatment')}</div>
                    <div className="text-sm font-medium text-gray-900">
                      {t(`vat_${accountingIntent.vat_treatment}` as Parameters<typeof t>[0])}
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <div className="text-xs text-gray-500 mb-1">{t('deductible')}</div>
                    <div className="text-sm font-medium text-gray-900">
                      {accountingIntent.is_deductible ? (
                        <span className="inline-flex items-center gap-1 text-green-700">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          {t('deductibleYes')}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-700">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          {t('deductibleNo')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Suggested konta */}
                {accountingIntent.suggested_konta && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('suggestedKonta')}</div>
                      {!editingKonta ? (
                        <button
                          onClick={() => {
                            setEditedDebit([...(accountingIntent.suggested_konta.debit || [])]);
                            setEditedCredit([...(accountingIntent.suggested_konta.credit || [])]);
                            setEditingKonta(true);
                          }}
                          className="text-xs text-violet-600 hover:text-violet-700 font-medium"
                        >
                          {t('editKonta')}
                        </button>
                      ) : (
                        <div className="flex gap-2">
                          <button
                            onClick={() => setEditingKonta(false)}
                            className="text-xs text-gray-500 hover:text-gray-700 font-medium"
                          >
                            {t('cancelEdit')}
                          </button>
                          <button
                            disabled={isSavingKonta}
                            onClick={async () => {
                              setIsSavingKonta(true);
                              try {
                                const updated = await updateAccountingIntent(id, {
                                  suggested_konta: { debit: editedDebit, credit: editedCredit },
                                });
                                setAccountingIntent(updated);
                                setEditingKonta(false);
                                setToast({ message: t('kontaSaved'), type: 'success' });
                              } catch {
                                setToast({ message: t('kontaSaveError'), type: 'error' });
                              } finally {
                                setIsSavingKonta(false);
                              }
                            }}
                            className="text-xs text-white bg-violet-600 hover:bg-violet-700 px-2 py-1 rounded font-medium disabled:opacity-50"
                          >
                            {isSavingKonta ? '...' : t('saveKonta')}
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {/* Debit */}
                      <div className="border border-blue-100 bg-blue-50/50 rounded-xl p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-blue-600">{t('debitSide')}</div>
                          {editingKonta && (
                            <button
                              onClick={() => setEditedDebit([...editedDebit, { konto: '', name: '', amount: '0' }])}
                              className="text-xs text-blue-600 hover:text-blue-700"
                            >+ {t('addRow')}</button>
                          )}
                        </div>
                        <div className="space-y-2">
                          {editingKonta ? editedDebit.map((entry, i) => (
                            <div key={i} className="flex items-center gap-2">
                              <input
                                value={entry.konto}
                                onChange={e => { const arr = [...editedDebit]; arr[i] = { ...arr[i], konto: e.target.value }; setEditedDebit(arr); }}
                                className="w-16 font-mono text-sm border border-gray-300 rounded px-1 py-0.5"
                                placeholder="5330"
                              />
                              <input
                                value={entry.name}
                                onChange={e => { const arr = [...editedDebit]; arr[i] = { ...arr[i], name: e.target.value }; setEditedDebit(arr); }}
                                className="flex-1 text-xs border border-gray-300 rounded px-1 py-0.5 min-w-0"
                                placeholder={t('kontoName')}
                              />
                              <input
                                value={entry.amount}
                                onChange={e => { const arr = [...editedDebit]; arr[i] = { ...arr[i], amount: e.target.value }; setEditedDebit(arr); }}
                                className="w-24 text-sm text-right border border-gray-300 rounded px-1 py-0.5 tabular-nums"
                                placeholder="0.00"
                              />
                              <button
                                onClick={() => setEditedDebit(editedDebit.filter((_, j) => j !== i))}
                                className="text-red-400 hover:text-red-600 text-xs"
                              >&times;</button>
                            </div>
                          )) : (accountingIntent.suggested_konta.debit || []).map((entry, i) => (
                            <div key={i} className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="font-mono text-sm font-semibold text-gray-900">{entry.konto}</div>
                                <div className="text-xs text-gray-500 truncate">{entry.name}</div>
                              </div>
                              <span className="text-sm font-medium text-gray-700 tabular-nums whitespace-nowrap">{formatAmountSr(entry.amount)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      {/* Credit */}
                      <div className="border border-emerald-100 bg-emerald-50/50 rounded-xl p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-medium text-emerald-600">{t('creditSide')}</div>
                          {editingKonta && (
                            <button
                              onClick={() => setEditedCredit([...editedCredit, { konto: '', name: '', amount: '0' }])}
                              className="text-xs text-emerald-600 hover:text-emerald-700"
                            >+ {t('addRow')}</button>
                          )}
                        </div>
                        <div className="space-y-2">
                          {editingKonta ? editedCredit.map((entry, i) => (
                            <div key={i} className="flex items-center gap-2">
                              <input
                                value={entry.konto}
                                onChange={e => { const arr = [...editedCredit]; arr[i] = { ...arr[i], konto: e.target.value }; setEditedCredit(arr); }}
                                className="w-16 font-mono text-sm border border-gray-300 rounded px-1 py-0.5"
                                placeholder="4330"
                              />
                              <input
                                value={entry.name}
                                onChange={e => { const arr = [...editedCredit]; arr[i] = { ...arr[i], name: e.target.value }; setEditedCredit(arr); }}
                                className="flex-1 text-xs border border-gray-300 rounded px-1 py-0.5 min-w-0"
                                placeholder={t('kontoName')}
                              />
                              <input
                                value={entry.amount}
                                onChange={e => { const arr = [...editedCredit]; arr[i] = { ...arr[i], amount: e.target.value }; setEditedCredit(arr); }}
                                className="w-24 text-sm text-right border border-gray-300 rounded px-1 py-0.5 tabular-nums"
                                placeholder="0.00"
                              />
                              <button
                                onClick={() => setEditedCredit(editedCredit.filter((_, j) => j !== i))}
                                className="text-red-400 hover:text-red-600 text-xs"
                              >&times;</button>
                            </div>
                          )) : (accountingIntent.suggested_konta.credit || []).map((entry, i) => (
                            <div key={i} className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="font-mono text-sm font-semibold text-gray-900">{entry.konto}</div>
                                <div className="text-xs text-gray-500 truncate">{entry.name}</div>
                              </div>
                              <span className="text-sm font-medium text-gray-700 tabular-nums whitespace-nowrap">{formatAmountSr(entry.amount)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* VAT breakdown */}
                {accountingIntent.vat_breakdown && Object.keys(accountingIntent.vat_breakdown).length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{t('vatBreakdown')}</div>
                    <div className="bg-gray-50 rounded-xl overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-xs text-gray-500 border-b border-gray-200">
                            <th className="text-left px-3 py-2 font-medium">{t('rate')}</th>
                            <th className="text-right px-3 py-2 font-medium">{t('base')}</th>
                            <th className="text-right px-3 py-2 font-medium">{t('tax')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(accountingIntent.vat_breakdown).map(([key, val]) => (
                            <tr key={key} className="border-b border-gray-100 last:border-0">
                              <td className="px-3 py-2 text-gray-900 font-medium">{key.replace('rate_', '')}%</td>
                              <td className="px-3 py-2 text-right text-gray-700 tabular-nums">{formatAmountSr(val.base)}</td>
                              <td className="px-3 py-2 text-right text-gray-700 tabular-nums">{formatAmountSr(val.tax)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* PDV Book Entry */}
                {accountingIntent.pdv_book_entries && accountingIntent.pdv_book_entries.book_type && (
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{t('pdvBookTitle')}</div>
                    <div className="bg-gray-50 rounded-xl p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold ${
                          accountingIntent.pdv_book_entries.book_type === 'KPR'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}>
                          {accountingIntent.pdv_book_entries.book_type === 'KPR' ? t('bookTypeKPR') : t('bookTypeKIR')}
                        </span>
                        <span className="text-xs text-gray-500">
                          {t('pdvPeriod')}: {accountingIntent.pdv_book_entries.period} · #{accountingIntent.pdv_book_entries.sequence}
                        </span>
                      </div>
                      {accountingIntent.pdv_book_entries.counterparty_name && (
                        <div className="text-sm text-gray-700">
                          {accountingIntent.pdv_book_entries.counterparty_name}
                          {accountingIntent.pdv_book_entries.counterparty_pib && (
                            <span className="text-gray-400 ml-1.5 font-mono text-xs">
                              PIB: {accountingIntent.pdv_book_entries.counterparty_pib}
                            </span>
                          )}
                        </div>
                      )}
                      {/* PP-PDV Fields */}
                      {accountingIntent.pdv_book_entries.pp_pdv_fields && Object.keys(accountingIntent.pdv_book_entries.pp_pdv_fields).length > 0 && (
                        <div className="bg-white rounded-lg overflow-hidden border border-gray-100">
                          <div className="px-3 py-1.5 bg-gray-50 border-b border-gray-100">
                            <span className="text-xs font-medium text-gray-500">{t('ppPdvFields')}</span>
                          </div>
                          <div className="divide-y divide-gray-50">
                            {Object.entries(accountingIntent.pdv_book_entries.pp_pdv_fields).map(([field, amount]) => (
                              <div key={field} className="flex items-center justify-between px-3 py-1.5">
                                <span className="text-xs font-mono text-gray-600">{field.replace(/_/g, ' ').replace('polje', 'Polje')}</span>
                                <span className="text-sm font-medium text-gray-900 tabular-nums">{formatAmountSr(String(amount))}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Confidence + review status */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium ${
                    parseFloat(accountingIntent.confidence) >= 0.75
                      ? 'bg-green-100 text-green-700'
                      : parseFloat(accountingIntent.confidence) >= 0.50
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-red-100 text-red-700'
                  }`}>
                    {t('intentConfidence')}: {parseFloat(accountingIntent.confidence) >= 0.75
                      ? tCommon('confidenceReliable')
                      : parseFloat(accountingIntent.confidence) >= 0.50
                        ? tCommon('confidenceReview')
                        : tCommon('confidenceUnreliable')}
                  </span>
                  {accountingIntent.requires_review && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-amber-100 text-amber-700">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {t('requiresReview')}
                    </span>
                  )}
                </div>

                {/* Review reasons */}
                {accountingIntent.review_reasons.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                    <div className="text-xs font-medium text-amber-700 mb-1.5">{t('reviewReasons')}</div>
                    <ul className="space-y-1">
                      {accountingIntent.review_reasons.map((reason, i) => (
                        <li key={i} className="text-sm text-amber-800 flex items-start gap-1.5">
                          <span className="mt-1.5 w-1 h-1 bg-amber-400 rounded-full shrink-0" />
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Approve / Reviewed state */}
                {accountingIntent.requires_review ? (
                  <button
                    onClick={handleReviewIntent}
                    disabled={isReviewingIntent}
                    className="w-full px-4 py-2.5 bg-green-600 text-white text-sm font-medium rounded-xl hover:bg-green-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {isReviewingIntent ? t('approving') : t('approveIntent')}
                  </button>
                ) : accountingIntent.reviewed_at && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {t('intentApproved')}
                  </div>
                )}
              </div>
            </FieldGroup>
          )}

          {/* Invoice info */}
          <FieldGroup
            title={t('invoiceInfo')}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
            collapsed={collapsedSections.has('invoice')}
            onToggle={() => toggleSection('invoice')}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <EditableField
                label={t('invoiceNumber')}
                value={getFieldValue('invoice_number', invoice.invoice_number)}
                onChange={(v) => setField('invoice_number', v)}
                confidence={getConfidence('invoice_number')}
                disabled={isProcessing}
                isDirty={isDirty('invoice_number')}
                onReset={() => resetField('invoice_number')}
              />
              <EditableField
                label={t('invoiceDate')}
                value={getFieldValue('invoice_date', invoice.invoice_date)}
                onChange={(v) => setField('invoice_date', v)}
                confidence={getConfidence('invoice_date')}
                disabled={isProcessing}
                type="date"
                isDirty={isDirty('invoice_date')}
                onReset={() => resetField('invoice_date')}
              />
              <EditableField
                label={t('dueDate')}
                value={getFieldValue('due_date', invoice.due_date)}
                onChange={(v) => setField('due_date', v)}
                confidence={getConfidence('due_date')}
                disabled={isProcessing}
                type="date"
                isDirty={isDirty('due_date')}
                onReset={() => resetField('due_date')}
              />
            </div>
          </FieldGroup>

          {/* Seller */}
          <FieldGroup
            title={t('sellerInfo')}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            }
            collapsed={collapsedSections.has('seller')}
            onToggle={() => toggleSection('seller')}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <EditableField
                label={t('pib')}
                value={getFieldValue('seller_pib', invoice.seller?.pib)}
                onChange={(v) => setField('seller_pib', v)}
                confidence={getConfidence('seller_pib')}
                disabled={isProcessing}
                isDirty={isDirty('seller_pib')}
                onReset={() => resetField('seller_pib')}
                validationStatus={getFieldWarning('seller_pib')}
              />
              <EditableField
                label={t('mb')}
                value={getFieldValue('seller_mb', invoice.seller?.mb)}
                onChange={(v) => setField('seller_mb', v)}
                disabled={isProcessing}
                isDirty={isDirty('seller_mb')}
                onReset={() => resetField('seller_mb')}
              />
              <EditableField
                label={t('companyName')}
                value={getFieldValue('seller_name', invoice.seller?.name)}
                onChange={(v) => setField('seller_name', v)}
                confidence={getConfidence('seller_name')}
                disabled={isProcessing}
                isDirty={isDirty('seller_name')}
                onReset={() => resetField('seller_name')}
              />
              <EditableField
                label={t('address')}
                value={getFieldValue('seller_address', invoice.seller?.address)}
                onChange={(v) => setField('seller_address', v)}
                confidence={getConfidence('seller_address')}
                disabled={isProcessing}
                isDirty={isDirty('seller_address')}
                onReset={() => resetField('seller_address')}
              />
              <EditableField
                label={t('city')}
                value={getFieldValue('seller_city', invoice.seller?.city)}
                onChange={(v) => setField('seller_city', v)}
                disabled={isProcessing}
                isDirty={isDirty('seller_city')}
                onReset={() => resetField('seller_city')}
              />
              <EditableField
                label={t('postalCode')}
                value={getFieldValue('seller_postal_code', invoice.seller?.postal_code)}
                onChange={(v) => setField('seller_postal_code', v)}
                disabled={isProcessing}
                isDirty={isDirty('seller_postal_code')}
                onReset={() => resetField('seller_postal_code')}
              />
            </div>
          </FieldGroup>

          {/* Buyer */}
          <FieldGroup
            title={t('buyerInfo')}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            }
            collapsed={collapsedSections.has('buyer')}
            onToggle={() => toggleSection('buyer')}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <EditableField
                label={t('pib')}
                value={getFieldValue('buyer_pib', invoice.buyer?.pib)}
                onChange={(v) => setField('buyer_pib', v)}
                confidence={getConfidence('buyer_pib')}
                disabled={isProcessing}
                isDirty={isDirty('buyer_pib')}
                onReset={() => resetField('buyer_pib')}
                validationStatus={getFieldWarning('buyer_pib')}
              />
              <EditableField
                label={t('mb')}
                value={getFieldValue('buyer_mb', invoice.buyer?.mb)}
                onChange={(v) => setField('buyer_mb', v)}
                disabled={isProcessing}
                isDirty={isDirty('buyer_mb')}
                onReset={() => resetField('buyer_mb')}
              />
              <EditableField
                label={t('companyName')}
                value={getFieldValue('buyer_name', invoice.buyer?.name)}
                onChange={(v) => setField('buyer_name', v)}
                confidence={getConfidence('buyer_name')}
                disabled={isProcessing}
                isDirty={isDirty('buyer_name')}
                onReset={() => resetField('buyer_name')}
              />
              <EditableField
                label={t('address')}
                value={getFieldValue('buyer_address', invoice.buyer?.address)}
                onChange={(v) => setField('buyer_address', v)}
                confidence={getConfidence('buyer_address')}
                disabled={isProcessing}
                isDirty={isDirty('buyer_address')}
                onReset={() => resetField('buyer_address')}
              />
              <EditableField
                label={t('city')}
                value={getFieldValue('buyer_city', invoice.buyer?.city)}
                onChange={(v) => setField('buyer_city', v)}
                disabled={isProcessing}
                isDirty={isDirty('buyer_city')}
                onReset={() => resetField('buyer_city')}
              />
              <EditableField
                label={t('postalCode')}
                value={getFieldValue('buyer_postal_code', invoice.buyer?.postal_code)}
                onChange={(v) => setField('buyer_postal_code', v)}
                disabled={isProcessing}
                isDirty={isDirty('buyer_postal_code')}
                onReset={() => resetField('buyer_postal_code')}
              />
            </div>
          </FieldGroup>

          {/* Amounts */}
          <FieldGroup
            title={t('amounts')}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            collapsed={collapsedSections.has('amounts')}
            onToggle={() => toggleSection('amounts')}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <EditableField
                label={t('subtotal')}
                value={getFieldValue('subtotal', invoice.subtotal)}
                onChange={(v) => setField('subtotal', v)}
                confidence={getConfidence('subtotal')}
                disabled={isProcessing}
                type="number"
                isDirty={isDirty('subtotal')}
                onReset={() => resetField('subtotal')}
                validationStatus={getFieldWarning('subtotal')}
              />
              <EditableField
                label={t('taxRate')}
                value={getFieldValue('tax_rate', invoice.tax_rate)}
                onChange={(v) => setField('tax_rate', v)}
                confidence={getConfidence('tax_rate')}
                disabled={isProcessing}
                type="number"
                isDirty={isDirty('tax_rate')}
                onReset={() => resetField('tax_rate')}
              />
              <EditableField
                label={t('taxAmount')}
                value={getFieldValue('tax_amount', invoice.tax_amount)}
                onChange={(v) => setField('tax_amount', v)}
                confidence={getConfidence('tax_amount')}
                disabled={isProcessing}
                type="number"
                isDirty={isDirty('tax_amount')}
                onReset={() => resetField('tax_amount')}
                validationStatus={getFieldWarning('tax_amount')}
              />
              <EditableField
                label={t('totalAmount')}
                value={getFieldValue('total_amount', invoice.total_amount)}
                onChange={(v) => setField('total_amount', v)}
                confidence={getConfidence('total_amount')}
                disabled={isProcessing}
                type="number"
                isDirty={isDirty('total_amount')}
                onReset={() => resetField('total_amount')}
                validationStatus={getFieldWarning('total_amount')}
              />
              {/* Currency dropdown */}
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <label className="text-xs font-medium text-gray-500">{t('currency')}</label>
                </div>
                <select
                  value={getFieldValue('currency', invoice.currency) ?? 'RSD'}
                  onChange={(e) => setField('currency', e.target.value)}
                  disabled={isProcessing}
                  className={`w-full px-3 py-2 bg-white border rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow ${
                    isProcessing ? 'bg-gray-50 text-gray-500 cursor-not-allowed border-gray-200' : ''
                  } ${isDirty('currency') ? 'border-violet-400 bg-violet-50/30' : 'border-gray-200'}`}
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>
            {/* Computed total check */}
            {computedTotal !== null && !isNaN(actualTotal) && (
              <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{t('computedTotal')}</span>
                  <span className="text-sm font-mono text-gray-600">
                    {formatAmountSr(computedTotal.toFixed(2), getFieldValue('currency', invoice.currency) ?? 'RSD')}
                  </span>
                </div>
                {(() => {
                  const diff = Math.abs(computedTotal - actualTotal);
                  if (diff < 0.5) {
                    return (
                      <span className="text-xs text-green-600 flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {t('mathMatch')}
                      </span>
                    );
                  }
                  return (
                    <span className="text-xs text-amber-600 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
                      </svg>
                      {t('mathMismatch', { diff: formatAmountSr(diff.toFixed(2)) })}
                    </span>
                  );
                })()}
              </div>
            )}
            {/* RSD equivalent for non-RSD invoices */}
            {invoice.currency !== 'RSD' && invoice.total_amount_rsd && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-3.5 h-3.5 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                  <span className="text-xs font-medium text-gray-500">{t('rsdEquivalent')}</span>
                </div>
                <div className="bg-violet-50/50 border border-violet-100 rounded-lg px-3 py-2">
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-semibold text-violet-700">
                      {formatAmountSr(invoice.total_amount_rsd, 'RSD')}
                    </span>
                    {invoice.exchange_rate && (
                      <span className="text-xs text-gray-500">
                        1 {invoice.currency} = {Number(invoice.exchange_rate).toFixed(4)} RSD
                      </span>
                    )}
                  </div>
                  {invoice.exchange_rate_date && (
                    <p className="text-xs text-gray-400 mt-1">
                      {t('nbsMiddleRate')} ({invoice.exchange_rate_date})
                    </p>
                  )}
                </div>
              </div>
            )}
          </FieldGroup>

          {/* Tax breakdown by rate */}
          {(getTaxGroups().length > 0 || !isProcessing) && (
            <FieldGroup
              title={t('taxBreakdown')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              }
              collapsed={collapsedSections.has('taxGroups')}
              onToggle={() => toggleSection('taxGroups')}
            >
              {getTaxGroups().length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-sm text-gray-500 mb-2">{tCommon('noData')}</p>
                  {!isProcessing && (
                    <button
                      onClick={addTaxGroup}
                      className="text-sm text-violet-600 hover:text-violet-700 font-medium"
                    >
                      + {t('addTaxGroup')}
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {getTaxGroups().map((group, i) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-500">
                          {t('taxGroupRate')}: {group.rate}%
                        </span>
                        {!isProcessing && (
                          <button
                            onClick={() => removeTaxGroup(i)}
                            className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                            title={t('removeTaxGroup')}
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="text-[10px] text-gray-400 mb-0.5 block">{t('taxGroupRate')} (%)</label>
                          <input
                            type="number"
                            value={group.rate}
                            onChange={(e) => setTaxGroup(i, 'rate', e.target.value)}
                            disabled={isProcessing}
                            className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-gray-400 mb-0.5 block">{t('taxGroupBase')}</label>
                          <input
                            type="number"
                            value={group.base_amount}
                            onChange={(e) => setTaxGroup(i, 'base_amount', e.target.value)}
                            disabled={isProcessing}
                            className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-gray-400 mb-0.5 block">{t('taxGroupTax')}</label>
                          <input
                            type="number"
                            value={group.tax_amount}
                            onChange={(e) => setTaxGroup(i, 'tax_amount', e.target.value)}
                            disabled={isProcessing}
                            className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  {!isProcessing && (
                    <button
                      onClick={addTaxGroup}
                      className="w-full py-2 text-sm text-violet-600 hover:text-violet-700 hover:bg-violet-50 font-medium rounded-xl transition-colors"
                    >
                      + {t('addTaxGroup')}
                    </button>
                  )}
                </div>
              )}
            </FieldGroup>
          )}

          {/* Line items */}
          <FieldGroup
            title={t('lineItems')}
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            }
            collapsed={collapsedSections.has('lineItems')}
            onToggle={() => toggleSection('lineItems')}
          >
            {getLineItems().length === 0 ? (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500 mb-2">{tCommon('noData')}</p>
                {!isProcessing && (
                  <button
                    onClick={addLineItem}
                    className="text-sm text-violet-600 hover:text-violet-700 font-medium"
                  >
                    + {t('addLineItem')}
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {(() => {
                  const items = getLineItems();
                  const hasTaxAmounts = items.some((item) => item.tax_amount != null);
                  return items.map((item, i) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-xl space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <input
                          value={item.description}
                          onChange={(e) => setLineItem(i, 'description', e.target.value)}
                          disabled={isProcessing}
                          placeholder={t('description')}
                          className="flex-1 px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                        />
                        {!isProcessing && (
                          <button
                            onClick={() => removeLineItem(i)}
                            className="p-1 text-gray-400 hover:text-red-500 transition-colors shrink-0"
                            title={t('removeItem')}
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>
                      <div className={`grid gap-2 ${hasTaxAmounts ? 'grid-cols-4' : 'grid-cols-3'}`}>
                        <div>
                          <label className="text-[10px] text-gray-400 mb-0.5 block">{t('quantity')}</label>
                          <input
                            type="number"
                            value={item.quantity ?? ''}
                            onChange={(e) => setLineItem(i, 'quantity', e.target.value)}
                            disabled={isProcessing}
                            className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-gray-400 mb-0.5 block">{t('unitPrice')}</label>
                          <input
                            type="number"
                            value={item.unit_price ?? ''}
                            onChange={(e) => setLineItem(i, 'unit_price', e.target.value)}
                            disabled={isProcessing}
                            className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                          />
                        </div>
                        {hasTaxAmounts && (
                          <div>
                            <label className="text-[10px] text-gray-400 mb-0.5 block">{t('itemTaxAmount')}</label>
                            <input
                              type="number"
                              value={item.tax_amount ?? ''}
                              onChange={(e) => setLineItem(i, 'tax_amount', e.target.value)}
                              disabled={isProcessing}
                              className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                            />
                          </div>
                        )}
                        <div>
                          <label className="text-[10px] text-gray-400 mb-0.5 block">{t('itemTotal')}</label>
                          <input
                            type="number"
                            value={item.total ?? ''}
                            onChange={(e) => setLineItem(i, 'total', e.target.value)}
                            disabled={isProcessing}
                            className="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:bg-gray-50 disabled:text-gray-500"
                          />
                        </div>
                      </div>
                    </div>
                  ));
                })()}
                {!isProcessing && (
                  <button
                    onClick={addLineItem}
                    className="w-full py-2 text-sm text-violet-600 hover:text-violet-700 hover:bg-violet-50 font-medium rounded-xl transition-colors"
                  >
                    + {t('addLineItem')}
                  </button>
                )}
              </div>
            )}
          </FieldGroup>

          {/* Payment modal */}
          {showPaymentModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center">
              <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowPaymentModal(false)} />
              <div className="relative bg-white rounded-2xl shadow-xl border border-gray-100 w-full max-w-md mx-4 p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">{t('recordPayment')}</h3>
                  <button onClick={() => setShowPaymentModal(false)} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Payment summary */}
                <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">{t('totalAmount')}</span>
                    <span className="font-semibold text-gray-900">
                      {invoice.total_amount ? new Intl.NumberFormat('sr-Latn-RS', { minimumFractionDigits: 2 }).format(parseFloat(invoice.total_amount)) : '—'} {invoice.currency}
                    </span>
                  </div>
                  {invoice.paid_amount && parseFloat(invoice.paid_amount) > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">{t('paidAmount')}</span>
                      <span className="font-medium text-green-600">
                        {new Intl.NumberFormat('sr-Latn-RS', { minimumFractionDigits: 2 }).format(parseFloat(invoice.paid_amount))} {invoice.currency}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-sm pt-1 border-t border-gray-200">
                    <span className="text-gray-500 font-medium">{t('remainingAmount')}</span>
                    <span className="font-bold text-red-600">
                      {new Intl.NumberFormat('sr-Latn-RS', { minimumFractionDigits: 2 }).format(
                        parseFloat(invoice.total_amount || '0') - parseFloat(invoice.paid_amount || '0')
                      )} {invoice.currency}
                    </span>
                  </div>
                </div>

                <PaymentForm
                  invoiceId={invoice.id}
                  totalAmount={invoice.total_amount}
                  paidAmount={invoice.paid_amount}
                  currency={invoice.currency}
                  onSuccess={() => {
                    setShowPaymentModal(false);
                    refresh();
                    setToast({ message: t('paymentRecorded'), type: 'success' });
                  }}
                />
              </div>
            </div>
          )}

          {/* Raw OCR output (debug) */}
          {invoice.raw_ocr_text && (
            <FieldGroup
              title={t('rawOcr')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              }
              collapsed={!collapsedSections.has('rawOcr')}
              onToggle={() => toggleSection('rawOcr')}
            >
              <pre className="text-xs text-gray-700 bg-gray-50 rounded-xl p-4 overflow-x-auto max-h-[500px] overflow-y-auto whitespace-pre-wrap break-words font-mono">
                {invoice.raw_ocr_text}
              </pre>
            </FieldGroup>
          )}

          {/* Raw LLM extraction output (debug) */}
          {invoice.raw_llm_output && (
            <FieldGroup
              title={t('rawLlm')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2 2 0 01-2 2H7a2 2 0 01-2-2v-2.5" />
                </svg>
              }
              collapsed={!collapsedSections.has('rawLlm')}
              onToggle={() => toggleSection('rawLlm')}
            >
              <pre className="text-xs text-gray-700 bg-gray-50 rounded-xl p-4 overflow-x-auto max-h-[500px] overflow-y-auto whitespace-pre-wrap break-words font-mono">
                {invoice.raw_llm_output}
              </pre>
            </FieldGroup>
          )}
        </div>
      </div>

      {/* Unsaved changes bar */}
      {hasChanges && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/90 backdrop-blur-lg border-t border-gray-200 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-gray-700">{t('unsavedChanges')}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={discardChanges}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                {t('discardChanges')}
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 disabled:opacity-50 transition-colors"
              >
                {isSaving ? tCommon('saving') : t('saveChanges')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowDeleteConfirm(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('deleteInvoice')}</h3>
            <p className="text-sm text-gray-600 mb-6">{t('deleteConfirm')}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                {isDeleting ? tCommon('deleting') : tCommon('delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {showExportDialog && (
        <ExportDialog
          invoiceIds={[id]}
          onClose={() => setShowExportDialog(false)}
        />
      )}
    </div>
  );
}

function FieldGroup({
  title,
  icon,
  collapsed,
  onToggle,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  collapsed: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-gray-50/50 transition-colors rounded-t-2xl"
      >
        <span className="text-gray-400">{icon}</span>
        <span className="text-sm font-semibold text-gray-900 flex-1">{title}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${collapsed ? '' : 'rotate-180'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {!collapsed && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

// ── Payment form ────────────────────────────────────────────────────

function PaymentForm({
  invoiceId,
  totalAmount,
  paidAmount,
  currency,
  onSuccess,
}: {
  invoiceId: string;
  totalAmount: string | null;
  paidAmount: string | null;
  currency: string;
  onSuccess: () => void;
}) {
  const t = useTranslations('detail');
  const [amount, setAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const remaining = totalAmount
    ? parseFloat(totalAmount) - parseFloat(paidAmount || '0')
    : 0;

  useEffect(() => {
    setAmount(remaining > 0 ? String(remaining) : '');
  }, [remaining]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) return;

    setSubmitting(true);
    setError('');
    try {
      const { recordPayment } = await import('@/lib/api/invoices');
      await recordPayment(invoiceId, {
        amount: parseFloat(amount),
        payment_date: paymentDate || undefined,
        notes: notes || undefined,
      });
      onSuccess();
      setNotes('');
    } catch (err: unknown) {
      const apiErr = err as { message?: string };
      setError(apiErr?.message || 'Greška pri evidentiranju uplate');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 pt-2 border-t border-gray-100">
      <p className="text-xs font-medium text-gray-700">{t('recordPayment')}</p>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <input
            type="number"
            step="0.01"
            min="0.01"
            max={remaining}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder={t('amount')}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
            required
          />
        </div>
        <div>
          <input
            type="date"
            value={paymentDate}
            onChange={(e) => setPaymentDate(e.target.value)}
            className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
          />
        </div>
      </div>
      <input
        type="text"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder={t('paymentNotes')}
        className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !amount || parseFloat(amount) <= 0}
        className="w-full py-1.5 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 rounded-lg transition-colors"
      >
        {submitting ? '...' : `${t('recordPayment')} (${amount || '0'} ${currency})`}
      </button>
    </form>
  );
}
