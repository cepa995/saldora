'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { useSearchParams, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useOrgPath } from '@/lib/navigation';
import { useOrganization } from '@/hooks/useOrganization';
import { useTeam } from '@/hooks/useTeam';
import { updateProfile, changePassword } from '@/lib/api/users';
import { updateMemberRole, removeMember } from '@/lib/api/team';
import { createInvitation, fetchInvitations, revokeInvitation, type InvitationInfo } from '@/lib/api/invitations';
import { fetchJoinRequests, approveJoinRequest, rejectJoinRequest, type JoinRequestInfo } from '@/lib/api/join-requests';
import { uploadLogo, deleteLogo } from '@/lib/api/organizations';
import { fetchMiniMaxConfig, saveMiniMaxConfig, testMiniMaxConnection } from '@/lib/api/export';
import { Toast, type ToastType } from '@/components/Toast';
import { UpgradeModal, type PlanErrorInfo } from '@/components/UpgradeModal';
import { isPlanError } from '@/lib/api-client';
import { formatRelativeTime } from '@/lib/formatters';
import { useNotifications } from '@/contexts/NotificationContext';

type SettingsTab = 'profile' | 'organization' | 'team' | 'integrations' | 'data-privacy';

const TABS: { key: SettingsTab; labelKey: string; adminOnly?: boolean }[] = [
  { key: 'profile', labelKey: 'profile' },
  { key: 'organization', labelKey: 'organization' },
  { key: 'team', labelKey: 'team', adminOnly: true },
  { key: 'integrations', labelKey: 'integrations', adminOnly: true },
  { key: 'data-privacy', labelKey: 'dataPrivacy' },
];

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations('settings');
  const { user } = useAuth();
  const orgPath = useOrgPath();

  const isAdmin = user?.role === 'admin';
  const { pendingJoinRequests } = useNotifications();
  const visibleTabs = TABS.filter((tab) => !tab.adminOnly || isAdmin);
  const tabParam = searchParams.get('tab') as SettingsTab | null;
  const activeTab = visibleTabs.find((tab) => tab.key === tabParam)?.key ?? 'profile';

  function switchTab(tab: SettingsTab) {
    router.push(orgPath(`/settings?tab=${tab}`), { scroll: false });
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
              className={`relative pb-3 text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === tab.key
                  ? 'text-violet-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t(tab.labelKey)}
              {tab.key === 'team' && pendingJoinRequests > 0 && (
                <span className="min-w-[20px] h-5 px-1.5 flex items-center justify-center bg-red-500 text-white text-[11px] font-bold rounded-full">
                  {pendingJoinRequests}
                </span>
              )}
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
      {activeTab === 'integrations' && isAdmin && <IntegrationsTab />}
      {activeTab === 'data-privacy' && <DataPrivacyTab />}
    </div>
  );
}

function ProfileTab() {
  const t = useTranslations('settings');
  const { user } = useAuth();
  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Profile form — overrides pattern (avoids setState in effect)
  const [profileOverrides, setProfileOverrides] = useState<Record<string, string>>({});
  const firstName = profileOverrides.firstName ?? user?.firstName ?? '';
  const lastName = profileOverrides.lastName ?? user?.lastName ?? '';

  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
  }

  async function handleSaveProfile() {
    setIsSaving(true);
    try {
      await updateProfile({ first_name: firstName, last_name: lastName });
      setProfileOverrides({});
      showToast(t('profileSaved'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : t('profileError');
      showToast(message, 'error');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleChangePassword() {
    if (newPassword !== confirmPassword) {
      showToast(t('passwordMismatch'), 'error');
      return;
    }
    setIsChangingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast(t('passwordChanged'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : t('passwordError');
      showToast(message, 'error');
    } finally {
      setIsChangingPassword(false);
    }
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
              onChange={(e) => setProfileOverrides((o) => ({ ...o, firstName: e.target.value }))}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('lastName')}</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setProfileOverrides((o) => ({ ...o, lastName: e.target.value }))}
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
          onClick={handleSaveProfile}
          disabled={isSaving}
          className="mt-4 px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? t('saving') : t('saveProfile')}
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
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('newPassword')}</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('confirmNewPassword')}</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleChangePassword}
            disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
            className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isChangingPassword ? t('saving') : t('changePassword')}
          </button>
        </div>
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}

function OrganizationTab() {
  const t = useTranslations('settings');
  const { user } = useAuth();
  const { data, isLoading, isSaving, error, saveError, save, refresh: refreshOrg } = useOrganization();
  const isAdmin = user?.role === 'admin';
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);
  const [isDeletingLogo, setIsDeletingLogo] = useState(false);

  // Track form edits as overrides on top of loaded data
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  const name = overrides.name ?? data?.name ?? '';
  const billingEmail = overrides.billingEmail ?? data?.billing_email ?? '';
  const pib = overrides.pib ?? data?.pib ?? '';

  function setName(v: string) { setOverrides((o) => ({ ...o, name: v })); }
  function setBillingEmail(v: string) { setOverrides((o) => ({ ...o, billingEmail: v })); }
  function setPib(v: string) { setOverrides((o) => ({ ...o, pib: v })); }

  function showOrgToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
  }

  async function handleSave() {
    const success = await save({
      name: name || undefined,
      billing_email: billingEmail || null,
      pib: pib || null,
    });
    if (success) setOverrides({});
    showOrgToast(success ? t('organizationSaved') : (saveError ?? t('organizationError')), success ? 'success' : 'error');
  }

  async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      showOrgToast(t('logoSizeLimit'), 'error');
      return;
    }
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      showOrgToast(t('logoFormats'), 'error');
      return;
    }
    setIsUploadingLogo(true);
    try {
      await uploadLogo(file);
      refreshOrg();
      showOrgToast(t('logoUploaded'), 'success');
    } catch {
      showOrgToast(t('logoError'), 'error');
    } finally {
      setIsUploadingLogo(false);
      e.target.value = '';
    }
  }

  async function handleLogoDelete() {
    setIsDeletingLogo(true);
    try {
      await deleteLogo();
      refreshOrg();
      showOrgToast(t('logoRemoved'), 'success');
    } catch {
      showOrgToast(t('logoError'), 'error');
    } finally {
      setIsDeletingLogo(false);
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="h-5 w-32 bg-gray-200 rounded animate-pulse mb-4" />
        <div className="space-y-4 max-w-lg">
          <div className="h-10 bg-gray-100 rounded-xl animate-pulse" />
          <div className="h-10 bg-gray-100 rounded-xl animate-pulse" />
          <div className="h-10 bg-gray-100 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-red-100 shadow-sm p-6">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Logo */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('logo')}</h2>
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-xl border border-gray-200 bg-gray-50 flex items-center justify-center overflow-hidden shrink-0">
            {data?.logo_url ? (
              <img src={data.logo_url} alt="Logo" className="w-full h-full object-cover" />
            ) : (
              <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
              </svg>
            )}
          </div>
          {isAdmin && (
            <div className="space-y-2">
              <div className="flex gap-2">
                <label className="px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors cursor-pointer disabled:opacity-50">
                  {isUploadingLogo ? t('saving') : t('uploadLogo')}
                  <input
                    type="file"
                    accept="image/png,image/jpeg"
                    onChange={handleLogoUpload}
                    disabled={isUploadingLogo}
                    className="hidden"
                  />
                </label>
                {data?.logo_url && (
                  <button
                    onClick={handleLogoDelete}
                    disabled={isDeletingLogo}
                    className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 rounded-xl transition-colors disabled:opacity-50"
                  >
                    {isDeletingLogo ? t('saving') : t('removeLogo')}
                  </button>
                )}
              </div>
              <p className="text-xs text-gray-400">PNG, JPG — max 2 MB</p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('organization')}</h2>
        <div className="space-y-4 max-w-lg">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('companyName')}</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!isAdmin}
              className={`w-full px-3 py-2 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent ${!isAdmin ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}`}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('pib')}</label>
            <input
              type="text"
              value={pib}
              onChange={(e) => setPib(e.target.value)}
              disabled={!isAdmin}
              className={`w-full px-3 py-2 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent ${!isAdmin ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}`}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('billingEmail')}</label>
            <input
              type="email"
              value={billingEmail}
              onChange={(e) => setBillingEmail(e.target.value)}
              disabled={!isAdmin}
              className={`w-full px-3 py-2 border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent ${!isAdmin ? 'bg-gray-50 cursor-not-allowed' : 'bg-white'}`}
            />
          </div>
          {data && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">{t('slug')}</label>
                <input
                  type="text"
                  value={data.slug}
                  disabled
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-500 cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">{t('plan')}</label>
                <input
                  type="text"
                  value={data.plan.charAt(0).toUpperCase() + data.plan.slice(1)}
                  disabled
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-500 cursor-not-allowed"
                />
              </div>
            </div>
          )}
          {isAdmin && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? t('saving') : t('saveOrganization')}
            </button>
          )}
        </div>
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}

const ROLE_LABELS: Record<string, string> = {
  admin: 'roleAdmin',
  manager: 'roleManager',
  operator: 'roleOperator',
  viewer: 'roleViewer',
};

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-violet-100 text-violet-700',
  manager: 'bg-blue-100 text-blue-700',
  operator: 'bg-amber-100 text-amber-700',
  viewer: 'bg-gray-100 text-gray-600',
};

function TeamTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const { members, isLoading, error, refresh } = useTeam();
  const { refreshJoinRequests } = useNotifications();
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('operator');
  const [isSendingInvite, setIsSendingInvite] = useState(false);
  const [pendingInvitations, setPendingInvitations] = useState<InvitationInfo[]>([]);
  const [invitationsLoaded, setInvitationsLoaded] = useState(false);
  const [joinRequests, setJoinRequests] = useState<JoinRequestInfo[]>([]);

  // Load invitations and join requests once on first render
  if (!invitationsLoaded && user?.role === 'admin') {
    setInvitationsLoaded(true);
    fetchInvitations().then(setPendingInvitations).catch(() => {});
    fetchJoinRequests().then(setJoinRequests).catch(() => {});
  }

  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
  }

  async function handleInvite() {
    if (!inviteEmail) return;
    setIsSendingInvite(true);
    try {
      await createInvitation({ email: inviteEmail, role: inviteRole });
      setInviteEmail('');
      showToast(t('inviteSent'), 'success');
      fetchInvitations().then(setPendingInvitations).catch(() => {});
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        const message = err && typeof err === 'object' && 'message' in err
          ? String(err.message) : 'Error';
        showToast(message, 'error');
      }
    } finally {
      setIsSendingInvite(false);
    }
  }

  async function handleRevokeInvitation(id: string) {
    try {
      await revokeInvitation(id);
      setPendingInvitations((prev) => prev.filter((inv) => inv.id !== id));
      showToast(t('inviteRevoked'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : 'Error';
      showToast(message, 'error');
    }
  }

  async function handleRoleChange(memberId: string, newRole: string) {
    try {
      await updateMemberRole(memberId, newRole);
      refresh();
      showToast(t('roleUpdated'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : 'Error';
      showToast(message, 'error');
    }
  }

  async function handleRemove(memberId: string) {
    try {
      await removeMember(memberId);
      setConfirmRemoveId(null);
      refresh();
      showToast(t('memberRemoved'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : 'Error';
      showToast(message, 'error');
    }
  }

  async function handleApproveJoinRequest(requestId: string) {
    try {
      await approveJoinRequest(requestId);
      setJoinRequests((prev) => prev.filter((r) => r.id !== requestId));
      refresh();
      refreshJoinRequests();
      showToast(t('requestApproved'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : 'Error';
      showToast(message, 'error');
    }
  }

  async function handleRejectJoinRequest(requestId: string) {
    try {
      await rejectJoinRequest(requestId);
      setJoinRequests((prev) => prev.filter((r) => r.id !== requestId));
      refreshJoinRequests();
      showToast(t('requestRejected'), 'success');
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : 'Error';
      showToast(message, 'error');
    }
  }

  return (
    <div className="space-y-6">
      {/* Team members */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">{t('teamMembers')}</h2>
        </div>

        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse" />
                <div className="flex-1 space-y-1">
                  <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
                  <div className="h-3 w-48 bg-gray-100 rounded animate-pulse" />
                </div>
                <div className="h-6 w-20 bg-gray-200 rounded-full animate-pulse" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-6">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : members.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p className="text-sm text-gray-500">{t('noTeamMembers')}</p>
          </div>
        ) : (
          <div>
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center gap-4 px-6 py-3.5 border-b border-gray-50 last:border-b-0"
              >
                {/* Avatar */}
                <div className="w-8 h-8 bg-violet-100 rounded-full flex items-center justify-center text-xs font-semibold text-violet-700 shrink-0">
                  {(member.first_name?.[0] ?? member.email[0]).toUpperCase()}
                </div>

                {/* Name & email */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {member.first_name || member.last_name
                      ? `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim()
                      : member.email}
                  </p>
                  <p className="text-xs text-gray-500 truncate">{member.email}</p>
                </div>

                {/* Role badge or dropdown */}
                {user?.role === 'admin' && member.id !== user?.id ? (
                  <select
                    value={member.role}
                    onChange={(e) => handleRoleChange(member.id, e.target.value)}
                    className="text-xs font-medium px-2 py-1 rounded-full border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                  >
                    {Object.entries(ROLE_LABELS).map(([value, labelKey]) => (
                      <option key={value} value={value}>{t(labelKey)}</option>
                    ))}
                  </select>
                ) : (
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${ROLE_COLORS[member.role] ?? ROLE_COLORS.viewer}`}>
                    {t(ROLE_LABELS[member.role] ?? 'roleViewer')}
                  </span>
                )}

                {/* Joined date */}
                <span className="text-xs text-gray-400 hidden sm:block w-20 text-right">
                  {formatRelativeTime(member.created_at)}
                </span>

                {/* Remove button */}
                {user?.role === 'admin' && member.id !== user?.id && (
                  <button
                    onClick={() => setConfirmRemoveId(member.id)}
                    className="text-xs text-red-500 hover:text-red-700 font-medium transition-colors"
                  >
                    {t('removeMember')}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Invite form */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4">{t('inviteMember')}</h2>
        <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
          <div className="flex-1">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder={t('inviteEmail')}
              className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
          </div>
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500"
          >
            {Object.entries(ROLE_LABELS).map(([value, labelKey]) => (
              <option key={value} value={value}>{t(labelKey)}</option>
            ))}
          </select>
          <button
            onClick={handleInvite}
            disabled={isSendingInvite || !inviteEmail}
            className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSendingInvite ? t('saving') : t('sendInvite')}
          </button>
        </div>

        {/* Pending invitations */}
        {pendingInvitations.length > 0 && (
          <div className="mt-4 border-t border-gray-100 pt-4">
            <h3 className="text-xs font-medium text-gray-500 mb-2">{t('pendingInvitations')}</h3>
            <div className="space-y-2">
              {pendingInvitations.map((inv) => (
                <div key={inv.id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-700">{inv.email}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROLE_COLORS[inv.role] ?? ROLE_COLORS.viewer}`}>
                      {t(ROLE_LABELS[inv.role] ?? 'roleViewer')}
                    </span>
                  </div>
                  <button
                    onClick={() => handleRevokeInvitation(inv.id)}
                    className="text-xs text-red-500 hover:text-red-700 font-medium transition-colors"
                  >
                    {tCommon('cancel')}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Pending join requests */}
      {joinRequests.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">{t('joinRequests')}</h2>
          <div className="space-y-3">
            {joinRequests.map((req) => (
              <div key={req.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl">
                <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center text-xs font-semibold text-amber-700 shrink-0">
                  {(req.user_name?.[0] ?? req.user_email?.[0] ?? '?').toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {req.user_name ?? req.user_email ?? '—'}
                  </p>
                  {req.user_name && req.user_email && (
                    <p className="text-xs text-gray-500 truncate">{req.user_email}</p>
                  )}
                  {req.message && (
                    <p className="text-xs text-gray-500 mt-0.5 italic truncate">&ldquo;{req.message}&rdquo;</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 hidden sm:block">
                  {formatRelativeTime(req.created_at)}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApproveJoinRequest(req.id)}
                    className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
                  >
                    {t('approve')}
                  </button>
                  <button
                    onClick={() => handleRejectJoinRequest(req.id)}
                    className="px-3 py-1.5 text-xs font-medium text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                  >
                    {t('reject')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Remove confirmation modal */}
      {confirmRemoveId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setConfirmRemoveId(null)} />
          <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('removeMember')}</h3>
            <p className="text-sm text-gray-600 mb-6">{t('removeMemberConfirm')}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmRemoveId(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={() => handleRemove(confirmRemoveId)}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                {tCommon('confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}

      {planError && (
        <UpgradeModal error={planError} onClose={() => setPlanError(null)} />
      )}
    </div>
  );
}

function IntegrationsTab() {
  const t = useTranslations('settings');
  const [selectedIntegration, setSelectedIntegration] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // MiniMax config state
  const [minimaxConfigLoaded, setMinimaxConfigLoaded] = useState(false);
  const [minimaxHasConfig, setMinimaxHasConfig] = useState(false);
  const [minimaxActive, setMinimaxActive] = useState(false);

  // Load MiniMax config status on mount
  useEffect(() => {
    fetchMiniMaxConfig()
      .then((config) => {
        setMinimaxHasConfig(true);
        setMinimaxActive(config.is_active);
      })
      .catch(() => {})
      .finally(() => setMinimaxConfigLoaded(true));
  }, []);

  const integrations = [
    {
      id: 'minimax',
      name: 'MiniMax',
      description: t('minimaxDesc'),
      logo: '/minimax-logo.png',
      icon: (
        <Image src="/minimax-logo.png" alt="MiniMax" width={24} height={24} className="object-contain" />
      ),
      connected: minimaxHasConfig && minimaxActive,
      loaded: minimaxConfigLoaded,
    },
    {
      id: 'sef',
      name: 'SEF (eFaktura)',
      description: t('sefDesc'),
      logo: null as string | null,
      icon: (
        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      ),
      connected: false,
      loaded: true,
      comingSoon: true,
    },
  ];

  // If an integration is selected, show its config form
  if (selectedIntegration === 'minimax') {
    return (
      <div className="space-y-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedIntegration(null)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          {t('backToIntegrations')}
        </button>

        <MiniMaxConfigForm
          toast={toast}
          setToast={setToast}
          onStatusChange={(hasConfig, isActive) => {
            setMinimaxHasConfig(hasConfig);
            setMinimaxActive(isActive);
          }}
        />

        {toast && (
          <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
        )}
      </div>
    );
  }

  // Integration cards grid
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {integrations.map((integration) => (
          <button
            key={integration.id}
            onClick={() => !integration.comingSoon && setSelectedIntegration(integration.id)}
            disabled={integration.comingSoon}
            className={`relative bg-white rounded-2xl border shadow-sm p-5 text-left transition-all ${
              integration.comingSoon
                ? 'border-gray-100 opacity-60 cursor-not-allowed'
                : 'border-gray-100 hover:border-violet-200 hover:shadow-md cursor-pointer'
            }`}
          >
            {/* Logo — bottom right */}
            {integration.logo && (
              <div className="absolute bottom-3 right-3 pointer-events-none">
                <Image src={integration.logo} alt={integration.name} width={64} height={64} className="object-contain" />
              </div>
            )}
            {/* Fallback icon for integrations without a logo */}
            {!integration.logo && (
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${
                integration.id === 'sef' ? 'bg-blue-100' : 'bg-gray-50 border border-gray-100'
              }`}>
                {integration.icon}
              </div>
            )}

            {/* Status / Coming soon badge */}
            {integration.comingSoon ? (
              <span className="absolute top-3 right-3 text-[10px] font-semibold uppercase tracking-wider bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                {t('comingSoon')}
              </span>
            ) : integration.loaded && (
              <span className={`absolute top-3 right-3 text-xs font-medium px-2.5 py-0.5 rounded-full ${
                integration.connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}>
                {integration.connected ? t('minimaxConnected') : t('minimaxDisconnected')}
              </span>
            )}

            {/* Name & description */}
            <h3 className="text-sm font-semibold text-gray-900 mb-1">{integration.name}</h3>
            <p className="text-xs text-gray-500 line-clamp-2">{integration.description}</p>

            {/* Configure arrow */}
            {!integration.comingSoon && (
              <div className="mt-3 flex items-center gap-1 text-xs font-medium text-violet-600">
                {t('configure')}
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            )}
          </button>
        ))}
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}

function MiniMaxConfigForm({
  toast,
  setToast,
  onStatusChange,
}: {
  toast: { message: string; type: 'success' | 'error' } | null;
  setToast: (t: { message: string; type: 'success' | 'error' } | null) => void;
  onStatusChange: (hasConfig: boolean, isActive: boolean) => void;
}) {
  const t = useTranslations('settings');

  const [configLoaded, setConfigLoaded] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [orgId, setOrgId] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [showSecrets, setShowSecrets] = useState(false);

  useEffect(() => {
    fetchMiniMaxConfig()
      .then((config) => {
        setHasConfig(true);
        setClientId(config.client_id);
        setUsername(config.username);
        setOrgId(String(config.minimax_org_id));
        setIsActive(config.is_active);
        setLastSync(config.last_sync_at);
      })
      .catch(() => {})
      .finally(() => setConfigLoaded(true));
  }, []);

  async function handleSave() {
    if (!clientId || !clientSecret || !username || !password || !orgId) {
      setToast({ message: t('allFieldsRequired'), type: 'error' });
      return;
    }
    setIsSaving(true);
    try {
      await saveMiniMaxConfig({
        client_id: clientId,
        client_secret: clientSecret,
        username,
        password,
        minimax_org_id: Number(orgId),
      });
      setHasConfig(true);
      setClientSecret('');
      setPassword('');
      onStatusChange(true, isActive);
      setToast({ message: t('configSaved'), type: 'success' });
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : t('configError');
      setToast({ message, type: 'error' });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleTest() {
    setIsTesting(true);
    try {
      const result = await testMiniMaxConnection();
      if (result.status === 'ok' || result.status === 'success' || result.status === 'connected') {
        setToast({ message: t('connectionSuccess'), type: 'success' });
      } else {
        setToast({ message: result.message || t('connectionFailed'), type: 'error' });
      }
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : t('connectionFailed');
      setToast({ message, type: 'error' });
    } finally {
      setIsTesting(false);
    }
  }

  if (!configLoaded) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="h-5 w-40 bg-gray-200 rounded animate-pulse mb-4" />
        <div className="space-y-4 max-w-lg">
          <div className="h-10 bg-gray-100 rounded-xl animate-pulse" />
          <div className="h-10 bg-gray-100 rounded-xl animate-pulse" />
          <div className="h-10 bg-gray-100 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      {/* Card header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-violet-100 rounded-xl flex items-center justify-center shrink-0">
            <svg className="w-5 h-5 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-gray-900">{t('minimaxTitle')}</h2>
        </div>
        <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${hasConfig && isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
          {hasConfig && isActive ? t('minimaxConnected') : t('minimaxDisconnected')}
        </span>
      </div>
      <p className="text-sm text-gray-500 mb-5 ml-12">{t('minimaxDesc')}</p>

      {/* Form fields */}
      <div className="space-y-4 max-w-lg">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{t('minimaxClientId')}</label>
          <input
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-medium text-gray-500">{t('minimaxClientSecret')}</label>
            <button
              type="button"
              onClick={() => setShowSecrets((s) => !s)}
              className="text-xs text-violet-600 hover:text-violet-700 font-medium transition-colors"
            >
              {showSecrets ? t('hideSecrets') : t('showSecrets')}
            </button>
          </div>
          <input
            type={showSecrets ? 'text' : 'password'}
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            placeholder={hasConfig ? '••••••••' : ''}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{t('minimaxUsername')}</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{t('minimaxPassword')}</label>
          <input
            type={showSecrets ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={hasConfig ? '••••••••' : ''}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">{t('minimaxOrgId')}</label>
          <input
            type="number"
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
          />
        </div>

        {/* Active toggle and last sync */}
        {hasConfig && (
          <div className="pt-2 border-t border-gray-100 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-900">{t('minimaxActive')}</p>
              <button
                type="button"
                onClick={() => setIsActive((a) => !a)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isActive ? 'bg-violet-600' : 'bg-gray-200'}`}
              >
                <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${isActive ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
            </div>
            {lastSync && (
              <p className="text-xs text-gray-400">
                {t('lastSync')}: {formatRelativeTime(lastSync)}
              </p>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-3 pt-2">
          {hasConfig && (
            <button
              onClick={handleTest}
              disabled={isTesting || isSaving}
              className="px-5 py-2 text-sm font-medium text-violet-700 bg-white border border-violet-300 rounded-xl hover:bg-violet-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTesting ? t('saving') : t('testConnection')}
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={isSaving || isTesting}
            className="px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? t('saving') : t('saveConfig')}
          </button>
        </div>
      </div>
    </div>
  );
}

function DataPrivacyTab() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);
  const [consents, setConsents] = useState<Record<string, boolean>>({});
  const [consentsLoaded, setConsentsLoaded] = useState(false);
  const [isToggling, setIsToggling] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deletionSubmitted, setDeletionSubmitted] = useState(false);

  // Load consent status on first render
  if (!consentsLoaded) {
    setConsentsLoaded(true);
    import('@/lib/api/compliance').then(({ fetchConsentStatus }) => {
      fetchConsentStatus()
        .then((statuses) => {
          const map: Record<string, boolean> = {};
          for (const s of statuses) map[s.consent_type] = s.granted;
          setConsents(map);
        })
        .catch(() => {});
    });
  }

  async function handleToggleConsent(type: string, granted: boolean) {
    setIsToggling(type);
    try {
      const { grantConsent, revokeConsent } = await import('@/lib/api/compliance');
      if (granted) {
        await grantConsent(type, '1.0');
      } else {
        await revokeConsent(type);
      }
      setConsents((prev) => ({ ...prev, [type]: granted }));
      setToast({ message: t('consentUpdated'), type: 'success' });
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : t('consentError');
      setToast({ message, type: 'error' });
    } finally {
      setIsToggling(null);
    }
  }

  async function handleDeleteAccount() {
    setIsDeleting(true);
    try {
      const { createDeletionRequest } = await import('@/lib/api/compliance');
      await createDeletionRequest();
      setDeletionSubmitted(true);
      setShowDeleteConfirm(false);
      setToast({ message: t('deletionRequestSubmitted'), type: 'success' });
    } catch (err) {
      const message = err && typeof err === 'object' && 'message' in err
        ? String(err.message) : t('deletionRequestError');
      setToast({ message, type: 'error' });
      setShowDeleteConfirm(false);
    } finally {
      setIsDeleting(false);
    }
  }

  function handleExport() {
    setToast({ message: tCommon('comingSoon'), type: 'info' });
  }

  const consentTypes = [
    { key: 'basic_processing', label: t('consentBasicProcessing'), description: t('consentBasicProcessingDesc'), disabled: true },
    { key: 'analytics', label: t('consentAnalytics'), description: t('consentAnalyticsDesc'), disabled: false },
    { key: 'marketing', label: t('consentMarketing'), description: t('consentMarketingDesc'), disabled: false },
  ];

  return (
    <div className="space-y-6">
      {/* Consent management */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-1">{t('consentManagement')}</h2>
        <p className="text-sm text-gray-500 mb-5">{t('consentManagementDesc')}</p>
        <div className="space-y-4">
          {consentTypes.map((ct) => (
            <div key={ct.key} className="flex items-start justify-between gap-4 py-2">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{ct.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{ct.description}</p>
              </div>
              <button
                onClick={() => !ct.disabled && handleToggleConsent(ct.key, !consents[ct.key])}
                disabled={ct.disabled || isToggling === ct.key}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0 ${
                  consents[ct.key] ? 'bg-violet-600' : 'bg-gray-200'
                } ${ct.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <span
                  className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                    consents[ct.key] ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-gray-100">
          <a
            href="/politika-privatnosti"
            target="_blank"
            className="text-sm text-violet-600 hover:text-violet-700 font-medium transition-colors"
          >
            {t('viewPrivacyPolicy')} &rarr;
          </a>
        </div>
      </div>

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
        {deletionSubmitted ? (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <p className="text-sm text-amber-800">{t('deletionRequestPending')}</p>
          </div>
        ) : (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded-xl hover:bg-red-700 transition-colors"
          >
            {t('deleteAccount')}
          </button>
        )}
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowDeleteConfirm(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('deleteAccount')}</h3>
            <p className="text-sm text-gray-600 mb-2">{t('deleteAccountConfirm')}</p>
            <p className="text-xs text-gray-500 mb-6">{t('deleteAccountRetention')}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                {tCommon('cancel')}
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors disabled:opacity-50"
              >
                {isDeleting ? t('saving') : tCommon('confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
