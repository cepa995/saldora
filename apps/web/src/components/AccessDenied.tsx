'use client';

import { useTranslations } from 'next-intl';

/**
 * Full-page access denied screen shown when a user navigates to a page
 * they don't have the required role for.
 */
export function AccessDenied() {
  const t = useTranslations('common');

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{t('accessDenied')}</h2>
      <p className="text-sm text-gray-500 max-w-sm">{t('accessDeniedDesc')}</p>
    </div>
  );
}
