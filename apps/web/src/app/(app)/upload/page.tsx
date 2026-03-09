'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { AccessDenied, FileUpload } from '@/components';

export default function UploadPage() {
  const t = useTranslations('upload');
  const { hasRole } = useAuth();
  const [hasFiles, setHasFiles] = useState(false);

  if (!hasRole('operator')) {
    return <AccessDenied />;
  }

  return (
    <div>
      {/* Page Title — shrinks once files are selected */}
      <div className={`text-center transition-all duration-300 ${hasFiles ? 'mb-4' : 'mb-10'}`}>
        <h1 className={`font-bold text-gray-900 transition-all duration-300 ${hasFiles ? 'text-2xl mb-1' : 'text-3xl mb-3'}`}>
          {t('title')}
        </h1>
        {!hasFiles && (
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">{t('subtitle')}</p>
        )}
      </div>

      {/* Upload Component */}
      <FileUpload onFileCountChange={(count) => setHasFiles(count > 0)} />

      {/* Info Section — hidden once files are present */}
      {!hasFiles && (
        <div className="mt-12 max-w-2xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="text-center p-4">
              <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{t('fastProcessing')}</h3>
              <p className="text-sm text-gray-600">{t('fastProcessingDesc')}</p>
            </div>

            <div className="text-center p-4">
              <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{t('scriptSupport')}</h3>
              <p className="text-sm text-gray-600">{t('scriptSupportDesc')}</p>
            </div>

            <div className="text-center p-4">
              <div className="w-12 h-12 bg-violet-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{t('secure')}</h3>
              <p className="text-sm text-gray-600">{t('secureDesc')}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
