'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { AccessDenied } from '@/components';
import {
  fetchTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
} from '@/lib/api/export';
import type {
  ExportTemplate,
  ExportTemplateCreate,
  ExportTemplateUpdate,
} from '@/lib/types/export';

// ── Available fields (matches backend INVOICE_HEADERS_SR) ─────────────────────

interface AvailableField {
  key: string;
  label: string;
}

const AVAILABLE_FIELDS: AvailableField[] = [
  { key: 'invoice_number', label: 'Broj fakture' },
  { key: 'invoice_date', label: 'Datum fakture' },
  { key: 'due_date', label: 'Datum valute' },
  { key: 'seller_name', label: 'Prodavac' },
  { key: 'seller_pib', label: 'PIB prodavca' },
  { key: 'seller_address', label: 'Adresa prodavca' },
  { key: 'seller_city', label: 'Grad prodavca' },
  { key: 'buyer_name', label: 'Kupac' },
  { key: 'buyer_pib', label: 'PIB kupca' },
  { key: 'subtotal', label: 'Osnovica' },
  { key: 'tax_rate', label: 'Stopa PDV (%)' },
  { key: 'tax_amount', label: 'Iznos PDV' },
  { key: 'total_amount', label: 'Ukupan iznos' },
  { key: 'currency', label: 'Valuta' },
  { key: 'status', label: 'Status' },
  { key: 'confidence_score', label: 'Pouzdanost (%)' },
];

const FORMAT_OPTIONS = ['xlsx', 'csv', 'json'] as const;

// ── TemplateCard ──────────────────────────────────────────────────────────────

function TemplateCard({
  template,
  t,
  onEdit,
  onDelete,
}: {
  template: ExportTemplate;
  t: ReturnType<typeof useTranslations<'templates'>>;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const visibleFields = template.fields
    .sort((a, b) => a.order - b.order)
    .slice(0, 3)
    .map((f) => f.label);
  const moreCount = template.fields.length - 3;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">
            {template.name}
          </h3>
          {template.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
              {template.description}
            </p>
          )}
        </div>
        <span
          className={`shrink-0 ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ring-1 ring-inset ${
            template.is_default
              ? 'bg-blue-50 text-blue-700 ring-blue-600/20'
              : 'bg-violet-50 text-violet-700 ring-violet-600/20'
          }`}
        >
          {template.is_default ? t('systemBadge') : t('customBadge')}
        </span>
      </div>

      <p className="text-xs text-gray-500 mb-2">
        {t('fieldCount', { count: template.fields.length })} &middot;{' '}
        {visibleFields.join(', ')}
        {moreCount > 0 && ` +${moreCount}`}
      </p>

      <div className="flex flex-wrap gap-1 mb-3">
        {(template.supported_formats ?? FORMAT_OPTIONS).map((fmt) => (
          <span
            key={fmt}
            className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 uppercase"
          >
            {fmt}
          </span>
        ))}
      </div>

      {!template.is_default && (
        <div className="flex gap-2 pt-3 border-t border-gray-100">
          <button
            onClick={onEdit}
            className="text-xs font-medium text-violet-600 hover:text-violet-700 transition-colors"
          >
            {t('editTemplate')}
          </button>
          <button
            onClick={onDelete}
            className="text-xs font-medium text-red-500 hover:text-red-600 transition-colors"
          >
            {t('deleteTemplate')}
          </button>
        </div>
      )}
    </div>
  );
}

// ── DeleteConfirmModal ────────────────────────────────────────────────────────

function DeleteConfirmModal({
  templateName,
  t,
  onConfirm,
  onCancel,
}: {
  templateName: string;
  t: ReturnType<typeof useTranslations<'templates'>>;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-xl max-w-sm w-full p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {t('deleteConfirmTitle')}
        </h3>
        <p className="text-sm text-gray-600 mb-6">
          {t('deleteConfirmMessage', { name: templateName })}
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Otkaži
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
          >
            {t('deleteTemplate')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── TemplateFormModal ─────────────────────────────────────────────────────────

interface SelectedField {
  key: string;
  label: string;
  order: number;
}

function TemplateFormModal({
  template,
  t,
  onSave,
  onCancel,
}: {
  template: ExportTemplate | null;
  t: ReturnType<typeof useTranslations<'templates'>>;
  onSave: (data: ExportTemplateCreate | ExportTemplateUpdate) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(template?.name ?? '');
  const [description, setDescription] = useState(template?.description ?? '');
  const [selectedFields, setSelectedFields] = useState<SelectedField[]>(() => {
    if (template?.fields?.length) {
      return [...template.fields].sort((a, b) => a.order - b.order);
    }
    return [];
  });
  const [formats, setFormats] = useState<string[]>(() => {
    if (template?.supported_formats?.length) return [...template.supported_formats];
    return [...FORMAT_OPTIONS];
  });
  const [error, setError] = useState('');

  const selectedKeys = new Set(selectedFields.map((f) => f.key));

  function toggleField(field: AvailableField) {
    if (selectedKeys.has(field.key)) {
      setSelectedFields((prev) => prev.filter((f) => f.key !== field.key));
    } else {
      setSelectedFields((prev) => [
        ...prev,
        { key: field.key, label: field.label, order: prev.length + 1 },
      ]);
    }
  }

  function moveField(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= selectedFields.length) return;
    setSelectedFields((prev) => {
      const arr = [...prev];
      [arr[index], arr[target]] = [arr[target], arr[index]];
      return arr.map((f, i) => ({ ...f, order: i + 1 }));
    });
  }

  function updateFieldLabel(index: number, label: string) {
    setSelectedFields((prev) =>
      prev.map((f, i) => (i === index ? { ...f, label } : f)),
    );
  }

  function removeField(index: number) {
    setSelectedFields((prev) =>
      prev.filter((_, i) => i !== index).map((f, i) => ({ ...f, order: i + 1 })),
    );
  }

  function toggleFormat(fmt: string) {
    setFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt],
    );
  }

  function handleSubmit() {
    if (!name.trim()) {
      setError(t('templateName'));
      return;
    }
    if (selectedFields.length === 0) {
      setError(t('noFieldsSelected'));
      return;
    }
    if (formats.length === 0) {
      setError(t('supportedFormats'));
      return;
    }
    setError('');

    const fields = selectedFields.map((f, i) => ({
      key: f.key,
      label: f.label,
      order: i + 1,
    }));

    if (template) {
      const update: ExportTemplateUpdate = {
        name: name.trim(),
        description: description.trim() || undefined,
        fields,
        supported_formats: formats,
      };
      onSave(update);
    } else {
      const create: ExportTemplateCreate = {
        name: name.trim(),
        description: description.trim() || undefined,
        fields,
        supported_formats: formats,
      };
      onSave(create);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          {template ? t('updateTemplate') : t('createTemplate')}
        </h3>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('templateName')}
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('templateNamePlaceholder')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none"
          />
        </div>

        {/* Description */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('templateDescription')}
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none resize-none"
          />
        </div>

        {/* Field selector */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('fieldsSection')}
          </label>
          <p className="text-xs text-gray-500 mb-2">{t('fieldsHelp')}</p>

          {/* Available fields as checkboxes */}
          <div className="mb-3">
            <p className="text-xs font-medium text-gray-500 mb-1.5">{t('fieldsList')}</p>
            <div className="grid grid-cols-2 gap-1.5">
              {AVAILABLE_FIELDS.map((field) => (
                <label
                  key={field.key}
                  className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors ${
                    selectedKeys.has(field.key)
                      ? 'bg-violet-50 text-violet-700'
                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedKeys.has(field.key)}
                    onChange={() => toggleField(field)}
                    className="rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                  />
                  {field.label}
                </label>
              ))}
            </div>
          </div>

          {/* Selected fields (ordered) */}
          {selectedFields.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1.5">
                {t('selectedFields', { count: selectedFields.length })}
              </p>
              <div className="space-y-1.5">
                {selectedFields.map((field, idx) => (
                  <div
                    key={field.key}
                    className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2"
                  >
                    <span className="text-xs text-gray-400 font-mono w-5 shrink-0">
                      {idx + 1}.
                    </span>
                    <input
                      type="text"
                      value={field.label}
                      onChange={(e) => updateFieldLabel(idx, e.target.value)}
                      className="flex-1 text-xs border-0 bg-transparent focus:ring-0 p-0 text-gray-700 outline-none"
                      title={t('customLabel')}
                    />
                    <div className="flex items-center gap-0.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => moveField(idx, -1)}
                        disabled={idx === 0}
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title={t('moveUp')}
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={() => moveField(idx, 1)}
                        disabled={idx === selectedFields.length - 1}
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title={t('moveDown')}
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={() => removeField(idx)}
                        className="p-1 text-gray-400 hover:text-red-500"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Supported formats */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            {t('supportedFormats')}
          </label>
          <div className="flex gap-3">
            {FORMAT_OPTIONS.map((fmt) => (
              <label
                key={fmt}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                  formats.includes(fmt)
                    ? 'bg-violet-50 text-violet-700'
                    : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formats.includes(fmt)}
                  onChange={() => toggleFormat(fmt)}
                  className="rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                />
                {fmt.toUpperCase()}
              </label>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Otkaži
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors"
          >
            {template ? t('updateTemplate') : t('createTemplate')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TemplatesPage() {
  const t = useTranslations('templates');
  const { hasRole } = useAuth();
  const [templates, setTemplates] = useState<ExportTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ExportTemplate | null>(null);
  const [deletingTemplate, setDeletingTemplate] = useState<ExportTemplate | null>(null);

  const loadTemplates = useCallback(async () => {
    try {
      const data = await fetchTemplates();
      setTemplates(data);
    } catch {
      setError('Greška pri učitavanju šablona');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  if (!hasRole('manager')) {
    return <AccessDenied />;
  }

  async function handleCreate(data: ExportTemplateCreate | ExportTemplateUpdate) {
    try {
      await createTemplate(data as ExportTemplateCreate);
      setFormOpen(false);
      await loadTemplates();
    } catch {
      setError('Greška pri kreiranju šablona');
    }
  }

  async function handleUpdate(data: ExportTemplateCreate | ExportTemplateUpdate) {
    if (!editingTemplate) return;
    try {
      await updateTemplate(editingTemplate.id, data as ExportTemplateUpdate);
      setEditingTemplate(null);
      await loadTemplates();
    } catch {
      setError('Greška pri ažuriranju šablona');
    }
  }

  async function handleDelete() {
    if (!deletingTemplate) return;
    try {
      await deleteTemplate(deletingTemplate.id);
      setDeletingTemplate(null);
      await loadTemplates();
    } catch {
      setError('Greška pri brisanju šablona');
    }
  }

  const systemTemplates = templates.filter((t) => t.is_default);
  const customTemplates = templates.filter((t) => !t.is_default);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="text-center sm:text-left">
          <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => {
            setEditingTemplate(null);
            setFormOpen(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-xl shadow-sm transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          {t('newTemplate')}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
          {error}
          <button onClick={() => setError('')} className="ml-2 underline">
            Zatvori
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-20">
          <svg
            className="w-12 h-12 text-gray-300 mx-auto mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M10.875 12c-.621 0-1.125.504-1.125 1.125M12 12c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125M12 15.375c0-.621-.504-1.125-1.125-1.125"
            />
          </svg>
          <p className="text-sm font-medium text-gray-600">{t('emptyState')}</p>
          <p className="text-xs text-gray-400 mt-1">{t('emptyStateSubtitle')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* System templates */}
          {systemTemplates.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 text-center sm:text-left">
                {t('systemBadge')}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {systemTemplates.map((tmpl) => (
                  <TemplateCard
                    key={tmpl.id}
                    template={tmpl}
                    t={t}
                    onEdit={() => {}}
                    onDelete={() => {}}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Custom templates */}
          <div>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 text-center sm:text-left">
              {t('customBadge')}
            </h2>
            {customTemplates.length === 0 ? (
              <p className="text-sm text-gray-400 py-4">{t('emptyState')}</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {customTemplates.map((tmpl) => (
                  <TemplateCard
                    key={tmpl.id}
                    template={tmpl}
                    t={t}
                    onEdit={() => setEditingTemplate(tmpl)}
                    onDelete={() => setDeletingTemplate(tmpl)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Form modal — create */}
      {formOpen && (
        <TemplateFormModal
          template={null}
          t={t}
          onSave={handleCreate}
          onCancel={() => setFormOpen(false)}
        />
      )}

      {/* Form modal — edit */}
      {editingTemplate && (
        <TemplateFormModal
          template={editingTemplate}
          t={t}
          onSave={handleUpdate}
          onCancel={() => setEditingTemplate(null)}
        />
      )}

      {/* Delete confirmation */}
      {deletingTemplate && (
        <DeleteConfirmModal
          templateName={deletingTemplate.name}
          t={t}
          onConfirm={handleDelete}
          onCancel={() => setDeletingTemplate(null)}
        />
      )}
    </div>
  );
}
