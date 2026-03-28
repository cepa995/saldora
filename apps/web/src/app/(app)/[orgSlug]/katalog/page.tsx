'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslations } from 'next-intl';
import {
  fetchProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  fetchMergeSuggestions,
  mergeProducts,
  type Product,
  type ProductCreate,
  type MergeSuggestion,
} from '@/lib/api/products';

// ── Formatting helpers ───────────────────────────────────────────────

function fmtPrice(n: number | null): string {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('sr-Latn-RS', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

function fmtPct(n: number | null): string {
  if (n === null || n === undefined) return '—';
  return `${n.toFixed(1)} %`;
}

// ── Toast ────────────────────────────────────────────────────────────

interface ToastState {
  message: string;
  type: 'success' | 'error';
}

// ── Create/Edit modal ────────────────────────────────────────────────

interface ProductModalProps {
  product: Product | null;
  onClose: () => void;
  onSaved: () => void;
  t: ReturnType<typeof useTranslations>;
  tc: ReturnType<typeof useTranslations>;
}

function ProductModal({ product, onClose, onSaved, t, tc }: ProductModalProps) {
  const [form, setForm] = useState<ProductCreate>({
    canonical_name: product?.canonical_name ?? '',
    unit_of_measure: product?.unit_of_measure ?? '',
    category: product?.category ?? '',
    aliases: product?.aliases ?? [],
    selling_price: product?.selling_price ?? undefined,
    default_margin_pct: product?.default_margin_pct ?? undefined,
  });
  const [aliasInput, setAliasInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof ProductCreate>(key: K, value: ProductCreate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function addAlias() {
    const trimmed = aliasInput.trim();
    if (trimmed && !form.aliases?.includes(trimmed)) {
      set('aliases', [...(form.aliases ?? []), trimmed]);
    }
    setAliasInput('');
  }

  function removeAlias(alias: string) {
    set('aliases', (form.aliases ?? []).filter((a) => a !== alias));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.canonical_name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const payload: ProductCreate = {
        canonical_name: form.canonical_name.trim(),
        unit_of_measure: form.unit_of_measure || undefined,
        category: form.category || undefined,
        aliases: form.aliases?.length ? form.aliases : undefined,
        selling_price: form.selling_price != null && String(form.selling_price) !== '' ? Number(form.selling_price) : undefined,
        default_margin_pct: form.default_margin_pct != null && String(form.default_margin_pct) !== '' ? Number(form.default_margin_pct) : undefined,
      };
      if (product) {
        await updateProduct(product.id, payload);
      } else {
        await createProduct(payload);
      }
      onSaved();
    } catch {
      setError(tc('error'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">
            {product ? tc('edit') : t('newProduct')}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">{t('productName')} *</label>
            <input
              type="text"
              required
              value={form.canonical_name}
              onChange={(e) => set('canonical_name', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('category')}</label>
              <select
                value={form.category ?? ''}
                onChange={(e) => set('category', e.target.value || undefined)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              >
                <option value="">—</option>
                <option value="hrana">{t('categories.hrana')}</option>
                <option value="pice">{t('categories.pice')}</option>
                <option value="materijal">{t('categories.materijal')}</option>
                <option value="ostalo">{t('categories.ostalo')}</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('unitOfMeasure')}</label>
              <input
                type="text"
                value={form.unit_of_measure ?? ''}
                onChange={(e) => set('unit_of_measure', e.target.value || undefined)}
                placeholder="kg, l, kom..."
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('sellingPrice')}</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.selling_price ?? ''}
                onChange={(e) => set('selling_price', e.target.value !== '' ? Number(e.target.value) : undefined)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('marginPct')}</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={form.default_margin_pct ?? ''}
                onChange={(e) => set('default_margin_pct', e.target.value !== '' ? Number(e.target.value) : undefined)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">{t('aliases')}</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={aliasInput}
                onChange={(e) => setAliasInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addAlias();
                  }
                }}
                placeholder="Dodaj alias..."
                className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
              />
              <button
                type="button"
                onClick={addAlias}
                className="px-3 py-2 text-sm text-violet-600 border border-violet-200 rounded-lg hover:bg-violet-50 transition-colors"
              >
                +
              </button>
            </div>
            {(form.aliases?.length ?? 0) > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {form.aliases?.map((alias) => (
                  <span
                    key={alias}
                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-full"
                  >
                    {alias}
                    <button
                      type="button"
                      onClick={() => removeAlias(alias)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {tc('cancel')}
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm bg-violet-600 text-white font-medium rounded-lg hover:bg-violet-700 disabled:opacity-60 transition-colors"
            >
              {saving ? tc('saving') : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Merge suggestions modal ──────────────────────────────────────────

interface MergeModalProps {
  onClose: () => void;
  onMerged: () => void;
  t: ReturnType<typeof useTranslations>;
  tc: ReturnType<typeof useTranslations>;
}

function MergeModal({ onClose, onMerged, t, tc }: MergeModalProps) {
  const [suggestions, setSuggestions] = useState<MergeSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [merging, setMerging] = useState<string | null>(null);
  const [merged, setMerged] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchMergeSuggestions()
      .then((res) => setSuggestions(res.suggestions))
      .finally(() => setLoading(false));
  }, []);

  async function handleMerge(s: MergeSuggestion) {
    const key = `${s.description_a}|${s.description_b}`;
    setMerging(key);
    try {
      await mergeProducts(s.suggested_canonical, [s.description_a, s.description_b]);
      setMerged((prev) => new Set([...prev, key]));
      onMerged();
    } finally {
      setMerging(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-gray-900">{t('mergeSuggestions')}</h2>
            <p className="text-xs text-gray-500 mt-0.5">{t('mergeSuggestionsDesc')}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-4">
          {loading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : suggestions.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">{t('noProducts')}</p>
          ) : (
            <div className="space-y-2">
              {suggestions.map((s) => {
                const key = `${s.description_a}|${s.description_b}`;
                const isMerged = merged.has(key);
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-4 px-4 py-3 rounded-xl border ${isMerged ? 'border-green-100 bg-green-50' : 'border-gray-100 bg-gray-50'}`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{s.description_a}</p>
                      <p className="text-xs text-gray-500">→ {s.description_b}</p>
                      <p className="text-xs text-violet-600 mt-0.5">
                        {t('similarity')}: {Math.round(s.similarity * 100)}%
                        {s.suggested_canonical && (
                          <span className="text-gray-400 ml-2">→ {s.suggested_canonical}</span>
                        )}
                      </p>
                    </div>
                    {isMerged ? (
                      <span className="text-xs text-green-600 font-medium shrink-0">{t('merged')}</span>
                    ) : (
                      <button
                        onClick={() => handleMerge(s)}
                        disabled={merging === key}
                        className="px-3 py-1.5 text-xs bg-violet-600 text-white font-medium rounded-lg hover:bg-violet-700 disabled:opacity-60 shrink-0 transition-colors"
                      >
                        {merging === key ? '...' : t('merge')}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 shrink-0 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {tc('close')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────

export default function KatalogPage() {
  const t = useTranslations('catalog');
  const tc = useTranslations('common');

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const searchTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  // Debounce search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => setDebouncedSearch(search), 300);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [search]);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProducts(categoryFilter || undefined, debouncedSearch || undefined);
      setProducts(data);
    } catch {
      setError(tc('error'));
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, debouncedSearch, tc]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  // Auto-clear toast
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  async function handleDelete(id: string) {
    try {
      await deleteProduct(id);
      setToast({ message: tc('success'), type: 'success' });
      setDeleteConfirm(null);
      loadProducts();
    } catch {
      setToast({ message: tc('error'), type: 'error' });
    }
  }

  function openCreate() {
    setEditingProduct(null);
    setModalOpen(true);
  }

  function openEdit(product: Product) {
    setEditingProduct(product);
    setModalOpen(true);
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-[100] px-4 py-3 rounded-xl text-sm font-medium shadow-lg transition-all ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMergeModalOpen(true)}
            className="px-4 py-2 text-sm text-violet-700 border border-violet-200 font-medium rounded-lg hover:bg-violet-50 transition-colors"
          >
            {t('mergeSuggestions')}
          </button>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 transition-colors"
          >
            {t('newProduct')}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={tc('search')}
          className="flex-1 max-w-xs px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 bg-white"
        >
          <option value="">{tc('all')}</option>
          <option value="hrana">{t('categories.hrana')}</option>
          <option value="pice">{t('categories.pice')}</option>
          <option value="materijal">{t('categories.materijal')}</option>
          <option value="ostalo">{t('categories.ostalo')}</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        {error ? (
          <div className="px-6 py-12 text-center">
            <p className="text-sm text-red-600">{error}</p>
            <button
              onClick={loadProducts}
              className="mt-3 text-sm text-violet-600 hover:underline"
            >
              {tc('retry')}
            </button>
          </div>
        ) : loading ? (
          <div className="animate-pulse">
            <div className="h-10 bg-gray-50 border-b border-gray-100" />
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex gap-4 px-4 py-3 border-b border-gray-100 last:border-0">
                <div className="h-4 bg-gray-200 rounded flex-1" />
                <div className="h-4 bg-gray-200 rounded w-20" />
                <div className="h-4 bg-gray-200 rounded w-12" />
                <div className="h-4 bg-gray-200 rounded w-24" />
              </div>
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
            <p className="text-sm text-gray-500">{t('noProducts')}</p>
            <button
              onClick={openCreate}
              className="mt-3 text-sm text-violet-600 hover:underline"
            >
              {t('newProduct')}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('productName')}</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('category')}</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('unitOfMeasure')}</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('sellingPrice')}</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('marginPct')}</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('aliases')}</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">{t('matchCount')}</th>
                  <th className="px-4 py-3 w-20" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-50/60 transition-colors group">
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-[200px] truncate">
                      {product.canonical_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {product.category ? (
                        <span className="px-2 py-0.5 bg-violet-50 text-violet-700 text-xs rounded-full font-medium">
                          {t(`categories.${product.category}` as Parameters<typeof t>[0]) ?? product.category}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{product.unit_of_measure ?? '—'}</td>
                    <td className="px-4 py-3 text-right text-gray-900 tabular-nums">
                      {fmtPrice(product.selling_price)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600 tabular-nums">
                      {fmtPct(product.default_margin_pct)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1 max-w-[180px]">
                        {product.aliases.slice(0, 3).map((alias) => (
                          <span key={alias} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                            {alias}
                          </span>
                        ))}
                        {product.aliases.length > 3 && (
                          <span className="text-xs text-gray-400">+{product.aliases.length - 3}</span>
                        )}
                        {product.aliases.length === 0 && <span className="text-gray-400">—</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600 tabular-nums">
                      {product.match_count}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => openEdit(product)}
                          className="p-1.5 text-gray-400 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors"
                          title={tc('edit')}
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(product.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title={tc('delete')}
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-2">{tc('confirm')}</h3>
            <p className="text-sm text-gray-600 mb-5">{t('confirmDelete')}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {tc('cancel')}
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 text-sm bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors"
              >
                {tc('delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Product modal */}
      {modalOpen && (
        <ProductModal
          product={editingProduct}
          onClose={() => { setModalOpen(false); setEditingProduct(null); }}
          onSaved={() => {
            setModalOpen(false);
            setEditingProduct(null);
            loadProducts();
            setToast({ message: tc('success'), type: 'success' });
          }}
          t={t}
          tc={tc}
        />
      )}

      {/* Merge suggestions modal */}
      {mergeModalOpen && (
        <MergeModal
          onClose={() => setMergeModalOpen(false)}
          onMerged={loadProducts}
          t={t}
          tc={tc}
        />
      )}
    </div>
  );
}
