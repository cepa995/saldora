'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api-client';

/**
 * Auth guard and slug validation layout for org-scoped pages.
 *
 * - Redirects unauthenticated users to /login
 * - Redirects users without an org to /register/organization
 * - Redirects slug mismatches to the correct org slug URL
 */
export default function OrgSlugLayout({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const t = useTranslations('common');
  const urlSlug = params.orgSlug as string;

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (!user?.organizationId) {
      router.push('/register/organization');
      return;
    }

    // Slug mismatch — redirect to correct slug, preserving the rest of the path
    if (user.orgSlug && urlSlug !== user.orgSlug) {
      const currentPath = window.location.pathname;
      const pathAfterSlug = currentPath.substring(currentPath.indexOf('/', 1));
      router.replace(`/${user.orgSlug}${pathAfterSlug || '/dashboard'}`);
    }
  }, [isLoading, isAuthenticated, user, urlSlug, router]);

  if (isLoading || !isAuthenticated || !user?.organizationId) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-violet-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-gray-500">{t('loading')}</span>
        </div>
      </div>
    );
  }

  // While redirecting due to slug mismatch, show loading
  if (user.orgSlug && urlSlug !== user.orgSlug) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-violet-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-gray-500">{t('loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <>
      {!user.emailVerified && <EmailVerificationBanner />}
      {children}
    </>
  );
}


function EmailVerificationBanner() {
  const t = useTranslations('common');
  const [resending, setResending] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleResend() {
    setResending(true);
    try {
      await apiClient('/api/v1/auth/resend-verification', { method: 'POST' });
      setSent(true);
    } catch {
      // Silently fail — rate limited or other error
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-amber-800">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          <span>
            {t('emailNotVerified')}
          </span>
        </div>
        {sent ? (
          <span className="text-sm text-emerald-700 font-medium">
            {t('verificationSent')}
          </span>
        ) : (
          <button
            onClick={handleResend}
            disabled={resending}
            className="text-sm font-medium text-amber-800 hover:text-amber-900 underline disabled:opacity-50"
          >
            {resending ? t('sending') : t('resendVerification')}
          </button>
        )}
      </div>
    </div>
  );
}
