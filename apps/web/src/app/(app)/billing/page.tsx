'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useBilling } from '@/hooks/useBilling';

/* -- Plan tier data ------------------------------------------------------ */

const PLANS = [
  {
    key: 'starter' as const,
    price: '25',
    invoiceLimit: 100,
    userLimit: 3,
    features: ['pricingFeatureOcr', 'pricingFeatureExport'],
    gradient: 'from-slate-500 to-slate-700',
    iconBg: 'bg-slate-100',
    iconColor: 'text-slate-600',
  },
  {
    key: 'professional' as const,
    price: '65',
    invoiceLimit: 500,
    userLimit: 10,
    popular: true,
    features: [
      'pricingFeatureOcr',
      'pricingFeatureExport',
      'pricingFeatureApi',
      'pricingFeatureSef',
      'pricingFeaturePriority',
    ],
    gradient: 'from-violet-600 to-indigo-600',
    iconBg: 'bg-violet-100',
    iconColor: 'text-violet-600',
  },
  {
    key: 'enterprise' as const,
    price: null,
    invoiceLimit: null,
    userLimit: null,
    features: ['pricingFeatureCustom', 'pricingFeatureSla', 'pricingFeaturePriority'],
    gradient: 'from-amber-500 to-orange-600',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600',
  },
];

/* -- Helpers ------------------------------------------------------------- */

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* -- Inline Icons -------------------------------------------------------- */

function CheckIcon() {
  return (
    <svg
      className="w-4 h-4 text-violet-500 shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function CreditCardIcon({ className = 'w-6 h-6' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
      />
    </svg>
  );
}

function ChartBarIcon({ className = 'w-6 h-6' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      />
    </svg>
  );
}

function SparklesIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  );
}

function RocketIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"
      />
    </svg>
  );
}

function BuildingIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
      />
    </svg>
  );
}

const PLAN_ICONS: Record<string, ({ className }: { className?: string }) => React.ReactNode> = {
  starter: SparklesIcon,
  professional: RocketIcon,
  enterprise: BuildingIcon,
};

/* -- Skeleton Components ------------------------------------------------- */

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gray-200" />
        <div className="h-4 bg-gray-200 rounded w-1/3" />
      </div>
      <div className="h-7 bg-gray-200 rounded w-1/2 mb-2" />
      <div className="h-3 bg-gray-200 rounded w-2/3" />
    </div>
  );
}

function SkeletonPlanCard() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-1/3 mb-3" />
      <div className="h-8 bg-gray-200 rounded w-1/2 mb-4" />
      <div className="space-y-2">
        <div className="h-4 bg-gray-100 rounded w-full" />
        <div className="h-4 bg-gray-100 rounded w-5/6" />
        <div className="h-4 bg-gray-100 rounded w-4/6" />
      </div>
      <div className="h-10 bg-gray-200 rounded-xl w-full mt-6" />
    </div>
  );
}

/* -- Main Page ----------------------------------------------------------- */

export default function BillingPage() {
  const { user } = useAuth();
  const { data, isLoading, error, refresh } = useBilling();
  const t = useTranslations('billing');
  const tLanding = useTranslations('landing');
  const tCommon = useTranslations('common');
  const [toast, setToast] = useState<string | null>(null);

  const isAdmin = user?.role === 'admin';

  // Non-admin guard
  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <p className="text-sm text-gray-500">{t('adminOnly')}</p>
        </div>
      </div>
    );
  }

  function handleUpgradeClick() {
    setToast(t('comingSoonDesc'));
    setTimeout(() => setToast(null), 4000);
  }

  const usagePercent =
    data && data.plan_limit
      ? Math.min(Math.round((data.monthly_usage / data.plan_limit) * 100), 100)
      : 0;

  const usageBarColor =
    usagePercent > 90
      ? 'from-red-500 to-red-600'
      : usagePercent > 70
        ? 'from-amber-400 to-amber-500'
        : 'from-violet-500 to-indigo-500';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg
              className="w-5 h-5 text-red-500 shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button
            onClick={refresh}
            className="text-sm font-medium text-red-700 hover:text-red-900 px-3 py-1 rounded-lg hover:bg-red-100 transition-colors"
          >
            {tCommon('retry')}
          </button>
        </div>
      )}

      {/* Current plan + Usage row */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Current plan card */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center">
                <CreditCardIcon className="w-5 h-5 text-violet-600" />
              </div>
              <h2 className="text-base font-semibold text-gray-900">{t('currentPlan')}</h2>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-semibold rounded-full shadow-sm">
                {data.plan === 'free'
                  ? t('freePlan')
                  : tLanding(`pricing${capitalize(data.plan)}`)}
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-3">{data.organization_name}</p>
          </div>

          {/* Usage card */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-indigo-600" />
              </div>
              <h2 className="text-base font-semibold text-gray-900">{t('usage')}</h2>
            </div>

            {data.plan_limit ? (
              <>
                <div className="flex items-baseline justify-between mb-2">
                  <span className="text-2xl font-bold text-gray-900 tabular-nums">
                    {data.monthly_usage}
                  </span>
                  <span className="text-sm text-gray-500">
                    / {data.plan_limit}
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-3 rounded-full bg-gradient-to-r ${usageBarColor} transition-all duration-700 ease-out`}
                    style={{ width: `${Math.max(usagePercent, 2)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {t('usagePercent', { percent: String(usagePercent) })}
                </p>
              </>
            ) : (
              <p className="text-sm text-gray-600">
                {t('invoicesUsedUnlimited', { used: String(data.monthly_usage) })}
              </p>
            )}
          </div>
        </div>
      ) : null}

      {/* Plans comparison */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-5">{t('plans')}</h2>
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SkeletonPlanCard />
            <SkeletonPlanCard />
            <SkeletonPlanCard />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PLANS.map((plan) => {
              const isCurrent = data?.plan === plan.key;
              const PlanIcon = PLAN_ICONS[plan.key];
              return (
                <div
                  key={plan.key}
                  className={`relative bg-white rounded-2xl border shadow-sm overflow-hidden hover:shadow-md transition-all duration-200 ${
                    plan.popular
                      ? 'border-violet-300 ring-2 ring-violet-100'
                      : 'border-gray-100'
                  }`}
                >
                  {/* Popular badge */}
                  {plan.popular && (
                    <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-center text-xs font-semibold py-1.5">
                      {t('popular')}
                    </div>
                  )}

                  <div className={`p-6 ${plan.popular ? 'pt-10' : ''}`}>
                    {/* Plan icon + name */}
                    <div className="flex items-center gap-3 mb-4">
                      <div
                        className={`w-10 h-10 rounded-xl ${plan.iconBg} flex items-center justify-center`}
                      >
                        <PlanIcon className={`w-5 h-5 ${plan.iconColor}`} />
                      </div>
                      <h3 className="text-lg font-bold text-gray-900">
                        {tLanding(`pricing${capitalize(plan.key)}`)}
                      </h3>
                    </div>

                    {/* Price */}
                    <div className="mb-5">
                      {plan.price ? (
                        <div className="flex items-baseline gap-1">
                          <span className="text-3xl font-bold text-gray-900">
                            &euro;{plan.price}
                          </span>
                          <span className="text-sm text-gray-500">{t('perMonth')}</span>
                        </div>
                      ) : (
                        <p className="text-lg font-semibold text-gray-700">{t('contactSales')}</p>
                      )}
                    </div>

                    {/* Divider */}
                    <div className="border-t border-gray-100 mb-5" />

                    {/* Features */}
                    <ul className="space-y-2.5">
                      <li className="flex items-center gap-2.5 text-sm text-gray-600">
                        <CheckIcon />
                        {plan.invoiceLimit
                          ? tLanding('pricingFeatureInvoices', {
                              count: String(plan.invoiceLimit),
                            })
                          : tLanding('pricingFeatureUnlimited')}
                      </li>
                      <li className="flex items-center gap-2.5 text-sm text-gray-600">
                        <CheckIcon />
                        {plan.userLimit
                          ? tLanding('pricingFeatureUsers', { count: String(plan.userLimit) })
                          : tLanding('pricingFeatureUnlimitedUsers')}
                      </li>
                      {plan.features.map((featureKey) => (
                        <li
                          key={featureKey}
                          className="flex items-center gap-2.5 text-sm text-gray-600"
                        >
                          <CheckIcon />
                          {tLanding(featureKey)}
                        </li>
                      ))}
                    </ul>

                    {/* CTA button */}
                    <div className="mt-6">
                      {isCurrent ? (
                        <span className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-violet-50 text-violet-700 text-sm font-semibold rounded-xl border border-violet-200">
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                          {t('yourPlan')}
                        </span>
                      ) : plan.key === 'enterprise' ? (
                        <button
                          onClick={handleUpgradeClick}
                          className="w-full px-4 py-2.5 border-2 border-amber-500 text-amber-700 text-sm font-medium rounded-xl hover:bg-amber-50 transition-colors"
                        >
                          {t('contactSales')}
                        </button>
                      ) : (
                        <button
                          onClick={handleUpgradeClick}
                          className={`w-full px-4 py-2.5 bg-gradient-to-r ${plan.gradient} text-white text-sm font-medium rounded-xl hover:shadow-lg hover:shadow-violet-500/25 hover:scale-[1.02] transition-all duration-200`}
                        >
                          {t('upgrade')}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm px-5 py-3.5 bg-gray-900 text-white text-sm rounded-xl shadow-2xl border border-gray-700/50 animate-[slideUp_0.3s_ease-out]">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center shrink-0 mt-0.5">
              <svg
                className="w-4 h-4 text-violet-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <p className="font-medium mb-0.5">{t('comingSoonTitle')}</p>
              <p className="text-gray-400 text-xs">{toast}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
