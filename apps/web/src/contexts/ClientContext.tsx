'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { fetchClients } from '@/lib/api/clients';
import { isPlanError } from '@/lib/api-client';
import type { ClientResponse } from '@/lib/types/client';

interface ClientContextValue {
  clients: ClientResponse[];
  selectedClientId: string | null;
  selectClient: (id: string | null) => void;
  isAgency: boolean;
  refresh: () => void;
}

const ClientContext = createContext<ClientContextValue>({
  clients: [],
  selectedClientId: null,
  selectClient: () => {},
  isAgency: false,
  refresh: () => {},
});

const STORAGE_KEY = 'saldora_selected_client';

/**
 * Provides client selection context for Agency organizations.
 *
 * Attempts to fetch clients on mount. If the endpoint returns a plan error
 * (non-Agency plan), sets isAgency=false and returns empty clients.
 */
export function ClientProvider({ children }: { children: React.ReactNode }) {
  const [clients, setClients] = useState<ClientResponse[]>([]);
  const [isAgency, setIsAgency] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Selection state was previously persisted in localStorage and read by the
  // sidebar dropdown. The dropdown was retired in favor of URL-based scoping
  // (/klijenti/{id}); selectedClientId is always null now. Clear any stale
  // value that a previous version may have left behind.
  useEffect(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* localStorage unavailable */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const result = await fetchClients({ is_active: true, per_page: 100 });
        if (cancelled) return;
        setClients(result.data);
        setIsAgency(true);
      } catch (err: unknown) {
        if (cancelled) return;
        if (isPlanError(err)) {
          setIsAgency(false);
          setClients([]);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const selectClient = useCallback(() => {
    /* no-op — selection is URL-driven now */
  }, []);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <ClientContext.Provider
      value={{
        clients,
        selectedClientId: null,
        selectClient,
        isAgency,
        refresh,
      }}
    >
      {children}
    </ClientContext.Provider>
  );
}

/**
 * Hook to access the client context.
 *
 * Returns:
 *   clients - Active clients for the organization.
 *   selectedClientId - Currently selected client ID (null = all).
 *   selectClient - Function to select a client.
 *   isAgency - Whether the user is on the Agency plan.
 *   refresh - Function to reload client list.
 */
export function useClient() {
  return useContext(ClientContext);
}
