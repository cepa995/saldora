'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { getPendingJoinRequestCount } from '@/lib/api/join-requests';

interface NotificationContextValue {
  pendingJoinRequests: number;
  refreshJoinRequests: () => void;
}

const NotificationContext = createContext<NotificationContextValue>({
  pendingJoinRequests: 0,
  refreshJoinRequests: () => {},
});

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [pendingJoinRequests, setPendingJoinRequests] = useState(0);
  const isAdmin = user?.role === 'admin';

  const refreshJoinRequests = useCallback(() => {
    if (!isAdmin) return;
    getPendingJoinRequestCount()
      .then((data) => setPendingJoinRequests(data.count))
      .catch(() => setPendingJoinRequests(0));
  }, [isAdmin]);

  // Fetch on mount / when role changes
  useEffect(() => {
    if (!isAdmin) return;
    getPendingJoinRequestCount()
      .then((data) => setPendingJoinRequests(data.count))
      .catch(() => setPendingJoinRequests(0));
  }, [isAdmin]);

  const value = useMemo(
    () => ({ pendingJoinRequests: isAdmin ? pendingJoinRequests : 0, refreshJoinRequests }),
    [pendingJoinRequests, refreshJoinRequests, isAdmin],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationContext);
}
