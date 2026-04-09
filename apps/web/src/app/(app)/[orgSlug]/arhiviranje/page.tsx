'use client';

import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { AccessDenied } from '@/components';
import ArchiveContent from './_components/ArchiveContent';

export default function ArhiviranjePage() {
  const t = useTranslations('archive');
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  if (!isAdmin) return <AccessDenied />;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">{t('title')}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{t('subtitle')}</p>
      </div>

      {/* Content */}
      <ArchiveContent />
    </div>
  );
}
