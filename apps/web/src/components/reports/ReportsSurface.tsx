'use client';

import { useState } from 'react';

import CatalogContent from '@/components/reports/CatalogContent';
import DpuContent from '@/components/reports/DpuContent';
import ReportContent from '@/components/reports/ReportContent';

type NavItem = {
  id: string;
  label: string;
  shortLabel: string;
  group: 'general' | 'hospitality' | 'management';
};

const NAV_ITEMS: NavItem[] = [
  { id: 'receivedGoods', label: 'Primljena roba', shortLabel: 'Primljena roba', group: 'general' },
  { id: 'spendingBySupplier', label: 'Potrošnja po dobavljačima', shortLabel: 'Po dobavljačima', group: 'general' },
  { id: 'monthlyBreakdown', label: 'Mesečni pregled stavki', shortLabel: 'Mesečni pregled', group: 'general' },
  { id: 'priceComparison', label: 'Poređenje cena', shortLabel: 'Poređenje cena', group: 'general' },
  { id: 'expenseSummary', label: 'Pregled troškova', shortLabel: 'Troškovi', group: 'general' },
  { id: 'kalkulacija', label: 'Kalkulacija cene', shortLabel: 'Kalkulacija', group: 'hospitality' },
  { id: 'ruc', label: 'Razlika u ceni (RUC)', shortLabel: 'RUC', group: 'hospitality' },
  { id: 'categorySpending', label: 'Potrošnja po kategorijama', shortLabel: 'Po kategorijama', group: 'hospitality' },
  { id: 'dpu', label: 'Dnevna evidencija robe', shortLabel: 'Dnevna evidencija', group: 'hospitality' },
  { id: 'catalog', label: 'Katalog proizvoda', shortLabel: 'Katalog', group: 'management' },
];

const GROUPS: { key: NavItem['group']; label: string; icon: React.ReactNode }[] = [
  {
    key: 'general',
    label: 'Opšti',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    key: 'hospitality',
    label: 'Nabavka i prodaja',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    key: 'management',
    label: 'Upravljanje',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
      </svg>
    ),
  },
];

const REPORT_IDS = NAV_ITEMS
  .filter((i) => i.group !== 'management' && i.id !== 'dpu')
  .map((i) => i.id);

interface Props {
  /** When set, scopes every report run to this client. */
  clientId?: string | null;
}

/**
 * Reports surface: group pills, report tabs, and the active template's panel.
 *
 * Used both by the client workspace Izveštaji tab (clientId scoped) and any
 * future agency-wide placement (no clientId → lifetime aggregates).
 */
export function ReportsSurface({ clientId }: Props) {
  const [activeGroup, setActiveGroup] = useState<NavItem['group']>('general');
  const [selected, setSelected] = useState<string>('receivedGoods');

  const groupItems = NAV_ITEMS.filter((i) => i.group === activeGroup);

  function handleGroupChange(group: NavItem['group']) {
    setActiveGroup(group);
    const firstInGroup = NAV_ITEMS.find((i) => i.group === group);
    if (firstInGroup) setSelected(firstInGroup.id);
  }

  return (
    <div className="space-y-4">
      {/* Group pills */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
        {GROUPS.map((g) => (
          <button
            key={g.key}
            onClick={() => handleGroupChange(g.key)}
            className={`inline-flex items-center gap-1.5 px-3 md:px-4 py-2 rounded-full text-xs md:text-sm font-medium whitespace-nowrap transition-all ${
              activeGroup === g.key
                ? 'bg-violet-600 text-white shadow-sm shadow-violet-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            {g.icon}
            {g.label}
          </button>
        ))}
      </div>

      {/* Report tabs (horizontal) */}
      <div className="border-b border-stone-200">
        <div className="flex gap-0 overflow-x-auto scrollbar-hide -mb-px">
          {groupItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelected(item.id)}
              className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                selected === item.id
                  ? 'border-violet-600 text-violet-700'
                  : 'border-transparent text-stone-500 hover:text-stone-700 hover:border-stone-300'
              }`}
            >
              {item.shortLabel}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div>
        {selected === 'catalog' && <CatalogContent />}
        {selected === 'dpu' && <DpuContent />}
        {REPORT_IDS.includes(selected) && (
          <ReportContent selectedTemplate={selected} clientId={clientId} />
        )}
      </div>
    </div>
  );
}
