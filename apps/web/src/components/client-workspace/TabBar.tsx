/**
 * Tab strip for the client workspace. Tab state lives in the URL so
 * navigation is stable and deep-linkable.
 */

'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

export type TabKey = 'timeline' | 'fakture' | 'izvestaji' | 'pravila';

const TABS: { key: TabKey; labelKey: string; icon: React.ReactNode }[] = [
  {
    key: 'timeline',
    labelKey: 'tabTimeline',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    key: 'fakture',
    labelKey: 'tabFakture',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    key: 'izvestaji',
    labelKey: 'tabIzvestaji',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    key: 'pravila',
    labelKey: 'tabPravila',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
];

interface Props {
  activeTab: TabKey;
  orgSlug: string;
  clientId: string;
}

export function TabBar({ activeTab, orgSlug, clientId }: Props) {
  const t = useTranslations('clientWorkspace');

  return (
    <div className="border-b border-stone-200 overflow-x-auto scrollbar-hide">
      <nav className="-mb-px flex gap-4 sm:gap-7">
        {TABS.map((tab) => {
          const isActive = tab.key === activeTab;
          const href =
            tab.key === 'timeline'
              ? `/${orgSlug}/klijenti/${clientId}`
              : `/${orgSlug}/klijenti/${clientId}?tab=${tab.key}`;
          return (
            <Link
              key={tab.key}
              href={href}
              className={`inline-flex items-center gap-2 whitespace-nowrap pb-3 pt-2 border-b-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'border-stone-900 text-stone-900'
                  : 'border-transparent text-stone-500 hover:text-stone-800 hover:border-stone-300'
              }`}
            >
              {/* Icons hidden below sm so all 4 labels fit on one row at 375px. */}
              <span className="hidden sm:inline-flex">{tab.icon}</span>
              {t(tab.labelKey)}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
