'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchSubscription } from '@/lib/api/billing';
import type { SubscriptionInfo } from '@/lib/types/billing';

interface UseBillingReturn {
  data: SubscriptionInfo | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches billing subscription data on mount.
 *
 * Returns:
 *   data - Subscription info or null while loading.
 *   isLoading - True during fetch.
 *   error - Error message if fetch failed, or null.
 *   refresh - Function to re-trigger fetch.
 */
export function useBilling(): UseBillingReturn {
  const [data, setData] = useState<SubscriptionInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await fetchSubscription();
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          const message =
            err && typeof err === 'object' && 'message' in err
              ? String(err.message)
              : 'Greška pri učitavanju podataka o pretplati';
          setError(message);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { data, isLoading, error, refresh };
}
