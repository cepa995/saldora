'use client';

import { useState } from 'react';
import Link from 'next/link';
import { FileUpload } from '@/components';

interface ProcessingResult {
  jobId: string;
  status: 'processing' | 'completed' | 'error';
  message?: string;
  extractedText?: string;
}

export default function UploadPage() {
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);

  const handleFileAccepted = (file: File) => {
    console.log('File accepted:', file.name);
    setProcessingResult(null);
  };

  const handleUploadStart = (file: File) => {
    console.log('Upload started:', file.name);
  };

  const handleUploadComplete = (file: File, jobId: string) => {
    console.log('Upload complete:', file.name, 'Job ID:', jobId);
    setProcessingResult({
      jobId,
      status: 'processing',
      message: 'OCR obrada je u toku. Molimo sačekajte...',
    });

    // TODO: Start polling for job status when backend is implemented
    // pollJobStatus(jobId);
  };

  const handleError = (error: string) => {
    console.error('Upload error:', error);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
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

        {/* Processing Result */}
        {processingResult && (
          <div className="mt-8 max-w-2xl mx-auto">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
              <div className="flex items-start gap-4">
                {processingResult.status === 'processing' && (
                  <svg
                    className="animate-spin h-6 w-6 text-blue-600 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                )}

                {processingResult.status === 'completed' && (
                  <svg className="h-6 w-6 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}

                <div className="flex-1">
                  <h3 className="text-lg font-medium text-gray-900">
                    {processingResult.status === 'processing' && 'Obrada u toku'}
                    {processingResult.status === 'completed' && 'Obrada završena'}
                    {processingResult.status === 'error' && 'Greška pri obradi'}
                  </h3>
                  {processingResult.message && (
                    <p className="mt-1 text-sm text-gray-600">{processingResult.message}</p>
                  )}
                  <p className="mt-2 text-xs text-gray-500">Job ID: {processingResult.jobId}</p>
                </div>
              </div>

              {/* OCR Result Preview - shown when completed */}
              {processingResult.status === 'completed' && processingResult.extractedText && (
                <div className="mt-4 pt-4 border-t border-blue-200">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Izvučeni tekst:</h4>
                  <pre className="text-sm text-gray-700 bg-white p-4 rounded-lg overflow-x-auto whitespace-pre-wrap">
                    {processingResult.extractedText}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="mt-12 max-w-2xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="text-center p-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Brza obrada</h3>
              <p className="text-sm text-gray-600">OCR obrada u nekoliko sekundi</p>
            </div>

            {/* Feature 2 */}
            <div className="text-center p-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
                  />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">Ćirilica i latinica</h3>
              <p className="text-sm text-gray-600">Podrška za oba pisma</p>
            </div>

            {/* Feature 3 */}
            <div className="text-center p-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
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
