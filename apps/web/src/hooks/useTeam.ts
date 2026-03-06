'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchTeamMembers } from '@/lib/api/team';
import type { TeamMember } from '@/lib/types/team';

interface UseTeamReturn {
  members: TeamMember[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches team members for the current organization.
 *
 * Returns:
 *   members - List of team members, or empty while loading.
 *   isLoading - True during initial fetch or refresh.
 *   error - Error message if fetch failed, or null.
 *   refresh - Function to re-fetch the member list.
 */
export function useTeam(): UseTeamReturn {
  const [members, setMembers] = useState<TeamMember[]>([]);
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
        const result = await fetchTeamMembers();
        if (!cancelled) setMembers(result);
      } catch (err) {
        if (!cancelled) {
          const message =
            err && typeof err === 'object' && 'message' in err
              ? String(err.message)
              : 'Greška pri učitavanju članova tima';
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

  return { members, isLoading, error, refresh };
}
