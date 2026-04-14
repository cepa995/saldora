'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';

export default function VerifyEmailPage() {
  const t = useTranslations('common');
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'checking' | 'success' | 'already' | 'error'>('checking');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }

    async function verify() {
      try {
        const result = await apiClient<{ message: string }>(
          `/api/v1/auth/verify?token=${encodeURIComponent(token!)}`,
          { method: 'GET' },
          true, // skip auth — verification link works without login
        );
        if (result.message.includes('već')) {
          setStatus('already');
        } else {
          setStatus('success');
        }
      } catch {
        setStatus('error');
      }
    }

    verify();
  }, [token]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        {status === 'checking' && (
          <div className="flex flex-col items-center gap-4">
            <svg className="animate-spin h-10 w-10 text-violet-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-gray-600">{t('verifyEmailChecking')}</p>
          </div>
        )}

        {status === 'success' && (
          <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-lg">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">{t('verifyEmailSuccess')}</h1>
            <p className="text-gray-600 mb-6">{t('verifyEmailSuccessDesc')}</p>
            <Link
              href="/login"
              className="inline-block px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-700 transition-colors"
            >
              {t('goToDashboard')}
            </Link>
          </div>
        )}

        {status === 'already' && (
          <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-lg">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">{t('verifyEmailAlready')}</h1>
            <Link
              href="/login"
              className="inline-block mt-4 px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-700 transition-colors"
            >
              {t('goToDashboard')}
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-lg">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">{t('verifyEmailFailed')}</h1>
            <p className="text-gray-600 mb-6">{t('verifyEmailFailedDesc')}</p>
            <Link
              href="/login"
              className="inline-block px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-700 transition-colors"
            >
              {t('goToDashboard')}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
