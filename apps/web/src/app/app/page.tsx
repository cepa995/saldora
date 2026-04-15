'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Redirect page for logged-in users.
 * Reads orgSlug from auth context and redirects to /{orgSlug}/dashboard.
 */
export default function AppRedirect() {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }

    if (!user?.organizationId || !user?.orgSlug) {
      router.replace('/register/organization');
      return;
    }

    router.replace(`/${user.orgSlug}/dashboard`);
  }, [user, isLoading, isAuthenticated, router]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex items-center justify-center">
      <svg className="animate-spin h-8 w-8 text-violet-600" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>
  );
}
