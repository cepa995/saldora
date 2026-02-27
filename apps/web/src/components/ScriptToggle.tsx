'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import type { Locale } from '@/i18n/config';

const LOCALE_OPTIONS: { value: Locale; labelKey: 'latin' | 'cyrillic' | 'english' }[] = [
  { value: 'sr-Latn', labelKey: 'latin' },
  { value: 'sr-Cyrl', labelKey: 'cyrillic' },
  { value: 'en', labelKey: 'english' },
];

interface ScriptToggleProps {
  collapsed?: boolean;
}

/**
 * Compact language/script toggle for the sidebar.
 *
 * Shows three segments (Lat | Ћир | Eng). Switches locale via cookie + router refresh.
 * In collapsed mode, shows only the active locale abbreviation.
 */
export function ScriptToggle({ collapsed = false }: ScriptToggleProps) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations('script');

  function switchLocale(newLocale: Locale) {
    if (newLocale === locale) return;
    // Setting cookie is an intentional side effect from user interaction
    // eslint-disable-next-line react-hooks/immutability
    document.cookie = `fakturaai_locale=${newLocale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Lax`;
    router.refresh();
  }

  if (collapsed) {
    const active = LOCALE_OPTIONS.find((o) => o.value === locale) ?? LOCALE_OPTIONS[0];
    const nextIdx = (LOCALE_OPTIONS.indexOf(active) + 1) % LOCALE_OPTIONS.length;
    const next = LOCALE_OPTIONS[nextIdx];
    return (
      <button
        onClick={() => switchLocale(next.value)}
        className="w-10 h-10 mx-auto flex items-center justify-center rounded-lg text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
        title={t(active.labelKey)}
        aria-label={t(active.labelKey)}
      >
        {t(active.labelKey)}
      </button>
    );
  }

  return (
    <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
      {LOCALE_OPTIONS.map((option) => (
        <button
          key={option.value}
          onClick={() => switchLocale(option.value)}
          className={`flex-1 px-2.5 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
            locale === option.value
              ? 'bg-white text-violet-700 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          aria-label={t(option.labelKey)}
          aria-pressed={locale === option.value}
        >
          {t(option.labelKey)}
        </button>
      ))}
    </div>
  );
}
