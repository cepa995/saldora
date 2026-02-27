'use client';

import { useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';

type SettingsTab = 'profile' | 'organization' | 'team' | 'data-privacy';

const TABS: { key: SettingsTab; labelKey: string; adminOnly?: boolean }[] = [
  { key: 'profile', labelKey: 'profile' },
  { key: 'organization', labelKey: 'organization' },
  { key: 'team', labelKey: 'team', adminOnly: true },
  { key: 'data-privacy', labelKey: 'dataPrivacy' },
];

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations('settings');
  const { user } = useAuth();

  const isAdmin = user?.role === 'admin';
  const visibleTabs = TABS.filter((tab) => !tab.adminOnly || isAdmin);
  const tabParam = searchParams.get('tab') as SettingsTab | null;
  const activeTab = visibleTabs.find((tab) => tab.key === tabParam)?.key ?? 'profile';

  function switchTab(tab: SettingsTab) {
    router.push(`/settings?tab=${tab}`, { scroll: false });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        {/* Desktop tabs */}
        <nav className="hidden sm:flex gap-6" aria-label="Settings tabs">
          {visibleTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => switchTab(tab.key)}
              className={`relative pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'text-violet-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t(tab.labelKey)}
              {activeTab === tab.key && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-violet-600 rounded-full" />
              )}
            </button>
          ))}
        </nav>

        {/* Mobile dropdown */}
        <div className="sm:hidden pb-3">
          <select
            value={activeTab}
            onChange={(e) => switchTab(e.target.value as SettingsTab)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500"
          >
            {visibleTabs.map((tab) => (
              <option key={tab.key} value={tab.key}>
                {t(tab.labelKey)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tab content */}
      {activeTab === 'profile' && <ProfileTab />}
      {activeTab === 'organization' && <OrganizationTab />}
      {activeTab === 'team' && isAdmin && <TeamTab />}
      {activeTab === 'data-privacy' && <DataPrivacyTab />}
    </div>
  );
}

function ProfileTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const [firstName, setFirstName] = useState(user?.firstName ?? '');
  const [lastName, setLastName] = useState(user?.lastName ?? '');
  const [toast, setToast] = useState<string | null>(null);

  function handleSave() {
    setToast(tCommon('comingSoon'));
    setTimeout(() => setToast(null), 3000);
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('profile')}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('firstName')}</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('lastName')}</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('email')}</label>
            <input
              type="email"
              value={user?.email ?? ''}
              disabled
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-500 cursor-not-allowed"
            />
            <p className="text-xs text-gray-400 mt-1">{t('emailReadonly')}</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          className="mt-4 px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors"
        >
          {t('saveProfile')}
        </button>
      </div>

      {/* Password change */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('changePassword')}</h2>
        <div className="space-y-3 max-w-md">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('currentPassword')}</label>
            <input
              type="password"
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('newPassword')}</label>
            <input
              type="password"
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('confirmNewPassword')}</label>
            <input
              type="password"
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSave}
            className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors"
          >
            {t('changePassword')}
          </button>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-xl shadow-lg animate-fade-in">
          {toast}
        </div>
      )}
    </div>
  );
}

function OrganizationTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [toast, setToast] = useState<string | null>(null);

  function handleSave() {
    setToast(tCommon('comingSoon'));
    setTimeout(() => setToast(null), 3000);
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">{t('organization')}</h2>
      <div className="space-y-4 max-w-lg">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{t('companyName')}</label>
          <input
            type="text"
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{t('billingEmail')}</label>
          <input
            type="email"
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>
        <button
          onClick={handleSave}
          className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors"
        >
          {t('saveOrganization')}
        </button>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-xl shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

function TeamTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [toast, setToast] = useState<string | null>(null);

  function handleInvite() {
    setToast(tCommon('comingSoon'));
    setTimeout(() => setToast(null), 3000);
  }

  return (
    <div className="space-y-6">
      {/* Team members table */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('teamMembers')}</h2>
        <div className="text-center py-8">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p className="text-sm text-gray-500">{t('noTeamMembers')}</p>
        </div>
      </div>

      {/* Invite form */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('inviteMember')}</h2>
        <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
          <div className="flex-1">
            <input
              type="email"
              placeholder={t('inviteEmail')}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <select className="px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500">
            <option value="member">{t('roleMember')}</option>
            <option value="admin">{t('roleAdmin')}</option>
          </select>
          <button
            onClick={handleInvite}
            className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors whitespace-nowrap"
          >
            {t('sendInvite')}
          </button>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-xl shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

function DataPrivacyTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  function handleExport() {
    setToast(tCommon('comingSoon'));
    setTimeout(() => setToast(null), 3000);
  }

  function handleDelete() {
    setToast(tCommon('comingSoon'));
    setTimeout(() => setToast(null), 3000);
    setShowDeleteConfirm(false);
  }

  return (
    <div className="space-y-6">
      {/* Export data */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-2">{t('exportData')}</h2>
        <p className="text-sm text-gray-500 mb-4">{t('exportDataDesc')}</p>
        <button
          onClick={handleExport}
          className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors"
        >
          {t('exportData')}
        </button>
      </div>

      {/* Delete account */}
      <div className="bg-white rounded-2xl border border-red-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-red-700 mb-2">{t('deleteAccount')}</h2>
        <p className="text-sm text-gray-500 mb-4">{t('deleteAccountWarning')}</p>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded-xl hover:bg-red-700 transition-colors"
        >
          {t('deleteAccount')}
        </button>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowDeleteConfirm(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('deleteAccount')}</h3>
            <p className="text-sm text-gray-600 mb-6">{t('deleteAccountConfirm')}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                {tCommon('confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-gray-900 text-white text-sm rounded-xl shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
