'use client';

import Link from 'next/link';

/**
 * Invoice list page placeholder.
 *
 * Will be fully implemented in Issue 8.3.
 */
export default function InvoicesPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-16 h-16 bg-violet-100 rounded-2xl flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
      </div>
      <h1 className="text-xl font-bold text-gray-900 mb-2">Fakture</h1>
      <p className="text-sm text-gray-500 mb-6 text-center max-w-md">
        Lista faktura sa filterima, pretragom i paginacijom.
        Ova stranica je u pripremi.
      </p>
      <Link
        href="/dashboard"
        className="text-sm font-medium text-violet-600 hover:text-violet-700 transition-colors"
      >
        ← Nazad na kontrolnu tablu
      </Link>
    </div>
  );
}
