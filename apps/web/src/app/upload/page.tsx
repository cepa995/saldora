'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FileUpload, PipelineStepper } from '@/components';
import type { PipelineStatus } from '@/components';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/contexts/AuthContext';

interface StatusResponse {
  id: string;
  status: 'uploaded' | 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  estimated_time: number | null;
  error_message: string | null;
  document_id: string | null;
  created_at: string;
}

const POLL_INTERVAL_ACTIVE_MS = 3000;
const POLL_INTERVAL_WAITING_MS = 5000;

export default function UploadPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login?callbackUrl=/upload');
    }
  }, [isLoading, isAuthenticated, router]);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const pollStatus = useCallback(
    (id: string) => {
      if (pollingRef.current) return;

      let currentInterval = POLL_INTERVAL_ACTIVE_MS;

      const poll = async () => {
        try {
          const data = await apiClient<StatusResponse>(`/api/v1/invoices/${id}/status`);

          // Map backend status → PipelineStatus
          const statusMap: Record<StatusResponse['status'], PipelineStatus> = {
            uploaded: 'uploaded',
            queued: 'queued',
            processing: 'processing',
            completed: 'review',
            failed: 'error',
          };
          const mapped = statusMap[data.status];
          setPipelineStatus(mapped);

          if (data.error_message) {
            setErrorMessage(data.error_message);
          }

          // Stop polling on terminal states
          if (data.status === 'completed' || data.status === 'failed') {
            stopPolling();
            return;
          }

          // Slow down polling when OCR isn't running
          const desiredInterval =
            data.status === 'uploaded'
              ? POLL_INTERVAL_WAITING_MS
              : POLL_INTERVAL_ACTIVE_MS;

          if (desiredInterval !== currentInterval) {
            currentInterval = desiredInterval;
            stopPolling();
            pollingRef.current = setInterval(poll, currentInterval);
          }
        } catch {
          // Silently continue polling on network errors
        }
      };

      poll();
      pollingRef.current = setInterval(poll, currentInterval);
    },
    [stopPolling]
  );

  const handleFileAccepted = () => {
    setInvoiceId(null);
    setPipelineStatus(null);
    setErrorMessage(undefined);
    stopPolling();
  };

  const handleUploadStart = () => {
    setPipelineStatus('uploading');
  };

  const handleUploadComplete = (_file: File, jobId: string) => {
    setInvoiceId(jobId);
    setPipelineStatus('uploaded');
    pollStatus(jobId);
  };

  const handleError = (error: string) => {
    setPipelineStatus('error');
    setErrorMessage(error);
    stopPolling();
  };

  // Show nothing while checking auth (prevents content flash)
  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <svg className="animate-spin h-8 w-8 text-violet-600" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-violet-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <span className="text-xl font-semibold text-gray-900">FakturaAI</span>
            </Link>

            <nav className="flex items-center gap-4">
              <Link
                href="/"
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                Početna
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Page Title */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Učitaj fakturu</h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Učitajte fakturu u PDF ili slikovnom formatu i naš AI će automatski izvući sve relevantne podatke.
          </p>
        </div>

        {/* Upload Component */}
        <FileUpload
          onFileAccepted={handleFileAccepted}
          onUploadStart={handleUploadStart}
          onUploadComplete={handleUploadComplete}
          onError={handleError}
        />

        {/* Pipeline Stepper — shown after upload starts */}
        {pipelineStatus && (
          <div className="mt-8 max-w-3xl mx-auto">
            <div className="border-gradient rounded-2xl">
              <div className="glass rounded-2xl p-8">
                <PipelineStepper currentStatus={pipelineStatus} errorMessage={errorMessage} />

                {/* Status-specific messages */}
                <div className="mt-6 text-center">
                  {pipelineStatus === 'uploading' && (
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <p className="text-sm text-gray-600">Fajl se otprema...</p>
                    </div>
                  )}

                  {pipelineStatus === 'uploaded' && (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                      <div className="flex items-start gap-3">
                        <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd"
                            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                            clipRule="evenodd" />
                        </svg>
                        <div className="text-left">
                          <p className="text-sm font-medium text-amber-800">
                            Fajl je uspešno sačuvan.
                          </p>
                          <p className="text-sm text-amber-700 mt-1">
                            OCR servis trenutno nije dostupan — obrada će početi automatski kada servis bude spreman.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {pipelineStatus === 'queued' && (
                    <p className="text-sm text-violet-600">
                      Faktura je u redu za obradu. Ovo može potrajati nekoliko trenutaka.
                    </p>
                  )}

                  {pipelineStatus === 'processing' && (
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <p className="text-sm text-violet-600">
                        OCR obrada je u toku. Ekstrahujemo podatke iz fakture...
                      </p>
                    </div>
                  )}

                  {pipelineStatus === 'review' && (
                    <div>
                      <p className="text-sm text-green-600 mb-4">
                        Obrada završena! Faktura je spremna za pregled.
                      </p>
                      {invoiceId && (
                        <Link
                          href={`/invoices/${invoiceId}`}
                          className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 transition-colors shadow-md shadow-violet-200"
                        >
                          Pregledaj fakturu
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </Link>
                      )}
                    </div>
                  )}

                  {pipelineStatus === 'error' && !errorMessage && (
                    <p className="text-sm text-red-600">
                      Došlo je do greške pri obradi fakture.
                    </p>
                  )}
                </div>

                {/* Invoice ID */}
                {invoiceId && (
                  <p className="mt-5 text-center text-xs text-gray-400">
                    ID: {invoiceId}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="mt-12 max-w-2xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="text-center p-4">
              <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Brza obrada</h3>
              <p className="text-sm text-gray-600">OCR obrada u nekoliko sekundi</p>
            </div>

            <div className="text-center p-4">
              <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Ćirilica i latinica</h3>
              <p className="text-sm text-gray-600">Podrška za oba pisma</p>
            </div>

            <div className="text-center p-4">
              <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Sigurno</h3>
              <p className="text-sm text-gray-600">Vaši podaci su zaštićeni</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            &copy; {new Date().getFullYear()} FakturaAI. Sva prava zadržana.
          </p>
        </div>
      </footer>
    </div>
  );
}
