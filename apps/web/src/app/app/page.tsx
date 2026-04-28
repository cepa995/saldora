'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { postAuthRoute } from '@/lib/auth';

/**
 * Redirect page for logged-in users. Defers the routing decision to
 * `postAuthRoute` so login, register, createOrganization, and this
 * fallback all agree on where a given user should land — including
 * routing pending-approval orgs to /awaiting-approval.
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

    router.replace(postAuthRoute(user));
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
