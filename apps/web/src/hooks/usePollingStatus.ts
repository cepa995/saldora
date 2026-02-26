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
const POLL_INTERVAL_MS = 2000;

interface UsePollingStatusOptions {
  onStatusUpdate: (jobId: string, status: ProcessingStatusResponse) => void;
  onError?: (jobId: string, error: unknown) => void;
}

/**
 * Polls the processing status endpoint for a set of invoice job IDs.
 *
 * Starts polling when jobIds are provided, stops when all reach
 * terminal states (completed/failed) or when the component unmounts.
 */
export function usePollingStatus(
  jobIds: string[],
  { onStatusUpdate, onError }: UsePollingStatusOptions,
) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const terminalRef = useRef<Set<string>>(new Set());

  const pollAll = useCallback(async () => {
    const activeIds = jobIds.filter((id) => !terminalRef.current.has(id));
    if (activeIds.length === 0) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    await Promise.allSettled(
      activeIds.map(async (jobId) => {
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
  }, [jobIds, onStatusUpdate, onError]);

  useEffect(() => {
    if (jobIds.length === 0) return;

    // Reset terminal tracking when job IDs change
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
