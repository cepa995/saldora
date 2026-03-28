'use client';

import { useState } from 'react';
import ReportContent from './_components/ReportContent';
import CatalogContent from './_components/CatalogContent';
import DpuContent from './_components/DpuContent';

// ── Sidebar data ─────────────────────────────────────────────────────

type SidebarItem = {
  id: string;
  label: string;
  group: 'general' | 'hospitality' | 'management';
};

const SIDEBAR_ITEMS: SidebarItem[] = [
  // Opšti izveštaji
  { id: 'receivedGoods', label: 'Primljena roba', group: 'general' },
  { id: 'spendingBySupplier', label: 'Potrošnja po dobavljačima', group: 'general' },
  { id: 'monthlyBreakdown', label: 'Mesečni pregled stavki', group: 'general' },
  { id: 'priceComparison', label: 'Poređenje cena', group: 'general' },
  { id: 'expenseSummary', label: 'Pregled troškova', group: 'general' },
  // Ugostiteljstvo
  { id: 'kalkulacija', label: 'Kalkulacija prodajne cene', group: 'hospitality' },
  { id: 'ruc', label: 'Razlika u ceni (RUC)', group: 'hospitality' },
  { id: 'categorySpending', label: 'Potrošnja po kategorijama', group: 'hospitality' },
  { id: 'dpu', label: 'Šank lista (DPU)', group: 'hospitality' },
  // Upravljanje
  { id: 'catalog', label: 'Katalog proizvoda', group: 'management' },
];

const GROUP_LABELS: Record<SidebarItem['group'], string> = {
  general: 'Opšti izveštaji',
  hospitality: 'Ugostiteljstvo',
  management: 'Upravljanje',
};

const REPORT_IDS = SIDEBAR_ITEMS
  .filter((i) => i.group !== 'management' && i.id !== 'dpu')
  .map((i) => i.id);

// ── Page ─────────────────────────────────────────────────────────────

/**
 * Unified Izveštaji page with a left sidebar for navigation and a
 * right content area that renders report tables, the product catalog,
 * or the DPU sheet depending on the selected item.
 *
 * Returns:
 *   A full-height flex layout with a fixed left sidebar and scrollable
 *   right content area.
 */
export default function IzvestajiPage() {
  const [selected, setSelected] = useState<string>('receivedGoods');

  return (
    <div className="flex min-h-0">
      {/* ── Left sidebar (static, within page flow) ────────────────── */}
      <aside className="hidden lg:block w-56 shrink-0 bg-white border-r border-gray-200 overflow-y-auto self-start sticky top-0 max-h-[calc(100vh-4rem)]">
        {/* Sidebar header */}
        <div className="px-3 py-3 border-b border-gray-100">
          <h1 className="text-sm font-bold text-gray-900">Izveštaji</h1>
          <p className="text-[10px] text-gray-500 mt-0.5">Analitika i upravljanje</p>
        </div>

        {/* Nav groups */}
        {(Object.entries(GROUP_LABELS) as [SidebarItem['group'], string][]).map(([group, label]) => (
          <div key={group} className="mb-1 pt-2">
            <div className="px-3 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
              {label}
            </div>
            {SIDEBAR_ITEMS.filter((i) => i.group === group).map((item) => (
              <button
                key={item.id}
                onClick={() => setSelected(item.id)}
                className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                  selected === item.id
                    ? 'bg-violet-50 text-violet-700 font-medium border-r-2 border-violet-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </aside>

      {/* ── Right content ──────────────────────────────────────────── */}
      <div className="flex-1 min-w-0">
        {/* Mobile: dropdown selector instead of sidebar */}
        <div className="lg:hidden px-4 pt-4 pb-2">
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500"
          >
            {(Object.entries(GROUP_LABELS) as [SidebarItem['group'], string][]).map(([group, label]) => (
              <optgroup key={group} label={label}>
                {SIDEBAR_ITEMS.filter((i) => i.group === group).map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <div className="p-4 lg:p-6">
          {selected === 'catalog' && <CatalogContent />}
          {selected === 'dpu' && <DpuContent />}
          {REPORT_IDS.includes(selected) && <ReportContent selectedTemplate={selected} />}
        </div>
      </div>
    </div>
  );
}
