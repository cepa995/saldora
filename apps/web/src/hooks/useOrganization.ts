'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchOrganization, updateOrganization } from '@/lib/api/organizations';
import type { OrganizationInfo, OrganizationUpdateRequest } from '@/lib/types/organization';

interface UseOrganizationReturn {
  data: OrganizationInfo | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  saveError: string | null;
  refresh: () => void;
  save: (update: OrganizationUpdateRequest) => Promise<boolean>;
}

/**
 * Fetches and manages the current user's organization settings.
 *
 * Returns:
 *   data - Organization info, or null while loading.
 *   isLoading - True during initial fetch or refresh.
 *   isSaving - True while an update request is in flight.
 *   error - Error message if fetch failed, or null.
 *   saveError - Error message if save failed, or null.
 *   refresh - Function to re-fetch organization data.
 *   save - Function to update organization settings. Returns true on success.
 */
export function useOrganization(): UseOrganizationReturn {
  const [data, setData] = useState<OrganizationInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
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
        const result = await fetchOrganization();
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          const message =
            err && typeof err === 'object' && 'message' in err
              ? String(err.message)
              : 'Greška pri učitavanju organizacije';
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

  const save = useCallback(async (update: OrganizationUpdateRequest): Promise<boolean> => {
    setIsSaving(true);
    setSaveError(null);

    try {
      const result = await updateOrganization(update);
      setData(result);
      return true;
    } catch (err) {
      const message =
        err && typeof err === 'object' && 'message' in err
          ? String(err.message)
          : 'Greška pri čuvanju podešavanja';
      setSaveError(message);
      return false;
    } finally {
      setIsSaving(false);
    }
  }, []);

  return { data, isLoading, isSaving, error, saveError, refresh, save };
}
