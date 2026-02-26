'use client';

import { useState } from 'react';
import { use } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useInvoiceDetail } from '@/hooks/useInvoiceDetail';
import { StatusBadge } from '@/components/StatusBadge';
import { DocumentViewer } from '@/components/DocumentViewer';
import { EditableField } from '@/components/EditableField';
import { formatAmountSr } from '@/lib/formatters';
import type { InvoiceUpdate, FieldConfidence } from '@/lib/types/invoice';

export default function InvoiceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations('detail');
  const tCommon = useTranslations('common');
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
  } = useInvoiceDetail(id);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());

  const isProcessing = invoice?.status === 'processing';
  const canVerify = invoice?.status === 'review';

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
        <Link href="/invoices" className="text-sm font-medium text-violet-600 hover:text-violet-700">
          {t('backToList')}
        </Link>
      </div>
    );
  }

  if (!invoice) return null;

  return (
    <div className="space-y-4">
      {/* Top bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/invoices"
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {t('backToList')}
          </Link>
          <div className="w-px h-5 bg-gray-200" />
          <h1 className="text-lg font-semibold text-gray-900">
            {invoice.invoice_number || '#—'}
          </h1>
          <StatusBadge status={invoice.status} />
        </div>

        <div className="flex items-center gap-2">
          {canVerify && (
            <button
              onClick={verify}
              disabled={isVerifying}
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-xl hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {isVerifying ? t('verifying') : t('verify')}
            </button>
          )}
          {hasChanges && (
            <button
              onClick={save}
              disabled={isSaving}
              className="px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? tCommon('saving') : t('saveChanges')}
            </button>
          )}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            disabled={isDeleting}
            className="px-4 py-2 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            {isDeleting ? tCommon('deleting') : t('deleteInvoice')}
          </button>
        </div>
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

      {/* Main content: document + form */}
      <div className="flex flex-col lg:flex-row gap-4" style={{ minHeight: '70vh' }}>
        {/* Document viewer */}
        <div className="lg:w-1/2 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="h-full min-h-[400px] lg:min-h-0">
            <DocumentViewer url={invoice.document_url} />
          </div>
        </div>

        {/* Data form */}
        <div className="lg:w-1/2 space-y-4 overflow-y-auto">
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
              />
              <EditableField
                label={t('invoiceDate')}
                value={getFieldValue('invoice_date', invoice.invoice_date)}
                onChange={(v) => setField('invoice_date', v)}
                confidence={getConfidence('invoice_date')}
                disabled={isProcessing}
                type="date"
              />
              <EditableField
                label={t('dueDate')}
                value={getFieldValue('due_date', invoice.due_date)}
                onChange={(v) => setField('due_date', v)}
                confidence={getConfidence('due_date')}
                disabled={isProcessing}
                type="date"
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
              />
              <EditableField
                label={t('companyName')}
                value={getFieldValue('seller_name', invoice.seller?.name)}
                onChange={(v) => setField('seller_name', v)}
                confidence={getConfidence('seller_name')}
                disabled={isProcessing}
              />
              <EditableField
                label={t('address')}
                value={getFieldValue('seller_address', invoice.seller?.address)}
                onChange={(v) => setField('seller_address', v)}
                confidence={getConfidence('seller_address')}
                disabled={isProcessing}
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
              />
              <EditableField
                label={t('companyName')}
                value={getFieldValue('buyer_name', invoice.buyer?.name)}
                onChange={(v) => setField('buyer_name', v)}
                confidence={getConfidence('buyer_name')}
                disabled={isProcessing}
              />
              <EditableField
                label={t('address')}
                value={getFieldValue('buyer_address', invoice.buyer?.address)}
                onChange={(v) => setField('buyer_address', v)}
                confidence={getConfidence('buyer_address')}
                disabled={isProcessing}
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
              />
              <EditableField
                label={t('taxRate')}
                value={getFieldValue('tax_rate', invoice.tax_rate)}
                onChange={(v) => setField('tax_rate', v)}
                confidence={getConfidence('tax_rate')}
                disabled={isProcessing}
                type="number"
              />
              <EditableField
                label={t('taxAmount')}
                value={getFieldValue('tax_amount', invoice.tax_amount)}
                onChange={(v) => setField('tax_amount', v)}
                confidence={getConfidence('tax_amount')}
                disabled={isProcessing}
                type="number"
              />
              <EditableField
                label={t('totalAmount')}
                value={getFieldValue('total_amount', invoice.total_amount)}
                onChange={(v) => setField('total_amount', v)}
                confidence={getConfidence('total_amount')}
                disabled={isProcessing}
                type="number"
              />
              <EditableField
                label={t('currency')}
                value={getFieldValue('currency', invoice.currency)}
                onChange={(v) => setField('currency', v)}
                disabled={isProcessing}
              />
            </div>
            {/* Total summary */}
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-500">{t('totalAmount')}</span>
              <span className="text-lg font-bold text-gray-900">
                {formatAmountSr(invoice.total_amount, invoice.currency)}
              </span>
            </div>
          </FieldGroup>

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
            {invoice.line_items.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">{tCommon('noData')}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-2 pr-3 text-xs font-medium text-gray-500">{t('description')}</th>
                      <th className="text-right py-2 px-3 text-xs font-medium text-gray-500">{t('quantity')}</th>
                      <th className="text-right py-2 px-3 text-xs font-medium text-gray-500">{t('unitPrice')}</th>
                      <th className="text-right py-2 pl-3 text-xs font-medium text-gray-500">{t('itemTotal')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.line_items.map((item, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-2.5 pr-3 text-gray-700">{item.description}</td>
                        <td className="py-2.5 px-3 text-right text-gray-600 font-mono">{item.quantity}</td>
                        <td className="py-2.5 px-3 text-right text-gray-600 font-mono">{formatAmountSr(item.unit_price)}</td>
                        <td className="py-2.5 pl-3 text-right text-gray-900 font-medium font-mono">{formatAmountSr(item.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </FieldGroup>
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
                onClick={save}
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
                onClick={() => {
                  setShowDeleteConfirm(false);
                  remove();
                }}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                {isDeleting ? tCommon('deleting') : tCommon('delete')}
              </button>
            </div>
          </div>
        </div>
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
