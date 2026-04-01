'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { AccessDenied } from '@/components';
import MonthlyExportContent from './_components/MonthlyExportContent';
import AuditExportContent from './_components/AuditExportContent';

type Tab = 'monthly' | 'audit';

export default function ArhiviranjePage() {
  const t = useTranslations('archive');
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [activeTab, setActiveTab] = useState<Tab>('monthly');

  if (!isAdmin) return <AccessDenied />;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{t('subtitle')}</p>
      </div>

      {/* Tab pills */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab('monthly')}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
            activeTab === 'monthly'
              ? 'bg-violet-600 text-white shadow-sm shadow-violet-200'
              : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50 hover:text-gray-900'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          {t('monthlyExportTitle')}
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
            activeTab === 'audit'
              ? 'bg-violet-600 text-white shadow-sm shadow-violet-200'
              : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50 hover:text-gray-900'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          {t('taxExportTitle')}
        </button>
      </div>

      {/* Content */}
      <div>
        {activeTab === 'monthly' && <MonthlyExportContent />}
        {activeTab === 'audit' && <AuditExportContent />}
      </div>
    </div>
  );
}
