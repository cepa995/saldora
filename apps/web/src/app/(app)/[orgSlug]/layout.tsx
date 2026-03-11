'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';

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

  return <>{children}</>;
}
