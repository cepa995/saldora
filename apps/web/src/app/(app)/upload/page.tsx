'use client';

import { FileUpload } from '@/components';

/**
 * Invoice upload page.
 *
 * Renders the file upload component with supporting info.
 * Auth guard and navigation are handled by the shared (app) layout.
 */
export default function UploadPage() {
  return (
    <div className="max-w-5xl mx-auto">
      {/* Page Title */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">Učitaj fakture</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Učitajte jednu ili više faktura u PDF ili slikovnom formatu i naš AI će
          automatski izvući sve relevantne podatke.
        </p>
      </div>

      {/* Upload Component */}
      <FileUpload />

      {/* Info Section */}
      <div className="mt-12 max-w-2xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg
                className="w-6 h-6 text-violet-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
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

          <div className="text-center p-4">
            <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg
                className="w-6 h-6 text-violet-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
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

          <div className="text-center p-4">
            <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg
                className="w-6 h-6 text-violet-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
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
    </div>
  );
}
