'use client';

import { useCallback, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api-client';

export interface ProcessingStatusResponse {
  id: string;
  status: 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  stage: string | null;
  estimated_time: number | null;
  error_message: string | null;
  document_id: string | null;
  created_at: string;
}

const TERMINAL_STATUSES = new Set(['completed', 'failed']);
const POLL_INTERVAL_MS = 10000;
const MAX_CONCURRENT_POLLS = 3;

interface UsePollingStatusOptions {
  onStatusUpdate: (jobId: string, status: ProcessingStatusResponse) => void;
  onError?: (jobId: string, error: unknown) => void;
}

/**
 * Polls the processing status endpoint for a set of invoice job IDs.
 *
 * Polls up to MAX_CONCURRENT_POLLS at a time to avoid overwhelming the API.
 * Stops when all reach terminal states (completed/failed) or on unmount.
 */
export function usePollingStatus(
  jobIds: string[],
  { onStatusUpdate, onError }: UsePollingStatusOptions,
) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const terminalRef = useRef<Set<string>>(new Set());
  const pollingRef = useRef(false);

  const pollAll = useCallback(async () => {
    // Prevent overlapping polls
    if (pollingRef.current) return;
    pollingRef.current = true;

    try {
      const activeIds = jobIds.filter((id) => !terminalRef.current.has(id));
      if (activeIds.length === 0) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return;
      }

      // Poll in batches of MAX_CONCURRENT_POLLS
      for (let i = 0; i < activeIds.length; i += MAX_CONCURRENT_POLLS) {
        const batch = activeIds.slice(i, i + MAX_CONCURRENT_POLLS);
        await Promise.allSettled(
          batch.map(async (jobId) => {
            try {
              const data = await apiClient<ProcessingStatusResponse>(
                `/api/v1/invoices/${jobId}/status`,
              );
              onStatusUpdate(jobId, data);
              if (TERMINAL_STATUSES.has(data.status)) {
                terminalRef.current.add(jobId);
              }
            } catch (err) {
              onError?.(jobId, err);
            }
          }),
        );
      }
    } finally {
      pollingRef.current = false;
    }
  }, [jobIds, onStatusUpdate, onError]);

  useEffect(() => {
    if (jobIds.length === 0) return;

    terminalRef.current = new Set();

    // Poll immediately, then on interval
    pollAll();
    intervalRef.current = setInterval(pollAll, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobIds, pollAll]);
}
