'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { AccessDenied } from '@/components';
import { useBilling } from '@/hooks/useBilling';

/* -- Plan tier data ------------------------------------------------------ */

const PLANS = [
  {
    key: 'starter' as const,
    monthlyPrice: 29,
    annualPrice: 24,
    invoiceLimit: 100,
    userLimit: 2,
    overage: '\u20AC0,10',
    icon: '\uD83D\uDE80',
    descKey: 'planDescStarter',
    features: [
      'pricingFeatureOcr',
      'pricingFeatureExport',
      'pricingFeatureMinimaxXml',
      'pricingFeatureNbs',
    ],
    popular: false,
  },
  {
    key: 'pro' as const,
    monthlyPrice: 79,
    annualPrice: 66,
    invoiceLimit: 400,
    userLimit: 5,
    overage: '\u20AC0,07',
    icon: '\u2B50',
    descKey: 'planDescPro',
    features: [
      'pricingFeatureOcr',
      'pricingFeatureAllExports',
      'pricingFeatureAccounting',
      'pricingFeatureSef',
      'pricingFeatureMinimaxPush',
      'pricingFeatureAuditExport',
      'pricingFeatureNbs',
    ],
    popular: true,
  },
  {
    key: 'agency' as const,
    monthlyPrice: 199,
    annualPrice: 165,
    invoiceLimit: 1500,
    userLimit: 15,
    overage: '\u20AC0,05',
    icon: '\uD83C\uDFE2',
    descKey: 'planDescAgency',
    features: [
      'pricingFeatureAllPro',
      'pricingFeatureAutomation',
      'pricingFeaturePriority',
    ],
    popular: false,
  },
];

/* -- Helpers ------------------------------------------------------------- */

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* -- Inline Icons -------------------------------------------------------- */

function CheckIcon({ className = 'text-emerald-600' }: { className?: string }) {
  return (
    <svg
      className={`w-3 h-3 ${className}`}
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
  const [annual, setAnnual] = useState(true);

  const isAdmin = user?.role === 'admin';

  // Non-admin guard
  if (!isAdmin) {
    return <AccessDenied />;
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
              {data.subscription_status && data.subscription_status !== 'active' && (
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  data.subscription_status === 'past_due'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  {t(`subscription${capitalize(data.subscription_status.replace('_', ''))}`)}
                </span>
              )}
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
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-900">{t('plans')}</h2>
          <div className="inline-flex items-center gap-1 p-1.5 bg-gray-100 rounded-full">
            <button
              onClick={() => setAnnual(false)}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${!annual ? 'bg-white shadow-md text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
            >
              {t('monthly')}
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 flex items-center gap-2 ${annual ? 'bg-white shadow-md text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
            >
              {t('annually')}
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full">-17%</span>
            </button>
          </div>
        </div>
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SkeletonPlanCard />
            <SkeletonPlanCard />
            <SkeletonPlanCard />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 items-start">
            {PLANS.map((plan) => {
              const isCurrent = data?.plan === plan.key;
              return (
                <div
                  key={plan.key}
                  className={`group relative p-8 rounded-3xl transition-all duration-500 hover:-translate-y-2 ${
                    plan.popular
                      ? 'bg-gradient-to-br from-gray-900 to-gray-800 text-white lg:scale-105 shadow-2xl shadow-violet-500/20 hover:shadow-violet-500/30 z-10'
                      : 'bg-white border border-gray-200/80 shadow-lg shadow-gray-200/50 hover:border-violet-200 hover:shadow-2xl hover:shadow-violet-200/30'
                  }`}
                >
                  {/* Glow effect for popular plan */}
                  {plan.popular && (
                    <div className="absolute -inset-px rounded-3xl bg-gradient-to-br from-violet-500 to-indigo-500 opacity-20 blur-xl group-hover:opacity-30 transition-opacity" />
                  )}

                  {/* Popular badge */}
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-gradient-to-r from-violet-500 to-indigo-500 text-white text-xs font-semibold rounded-full shadow-lg shadow-violet-500/30">
                      {t('popular')}
                    </div>
                  )}

                  <div className="relative">
                    {/* Icon and name */}
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl ${
                        plan.popular ? 'bg-white/10' : 'bg-gray-100'
                      }`}>
                        {plan.icon}
                      </div>
                      <div>
                        <h3 className={`text-xl font-bold ${plan.popular ? 'text-white' : 'text-gray-900'}`}>
                          {tLanding(`pricing${capitalize(plan.key)}`)}
                        </h3>
                        <p className={`text-sm ${plan.popular ? 'text-gray-400' : 'text-gray-500'}`}>
                          {t(plan.descKey)}
                        </p>
                      </div>
                    </div>

                    {/* Price */}
                    <div className={`mb-6 pb-6 border-b ${plan.popular ? 'border-gray-700' : 'border-gray-200'}`}>
                      <div className="flex items-baseline gap-1">
                        <span className={`text-5xl font-bold ${plan.popular ? 'text-white' : 'text-gray-900'}`}>
                          &euro;{annual ? plan.annualPrice : plan.monthlyPrice}
                        </span>
                        <span className={`text-sm ${plan.popular ? 'text-gray-400' : 'text-gray-500'}`}>
                          {annual ? t('perMonthAnnual') : t('perMonth')}
                        </span>
                      </div>
                      {annual && (
                        <p className={`text-sm mt-2 ${plan.popular ? 'text-emerald-400' : 'text-emerald-600'}`}>
                          {t('annualSavings', { amount: String((plan.monthlyPrice - plan.annualPrice) * 12) })}
                        </p>
                      )}
                    </div>

                    {/* Features */}
                    <ul className="space-y-3 mb-8">
                      <li className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${plan.popular ? 'bg-violet-500/20' : 'bg-emerald-100'}`}>
                          <CheckIcon className={plan.popular ? 'text-violet-300' : 'text-emerald-600'} />
                        </div>
                        <span className={`text-sm ${plan.popular ? 'text-gray-300' : 'text-gray-600'}`}>
                          {tLanding('pricingFeatureInvoices', { count: String(plan.invoiceLimit) })}
                        </span>
                      </li>
                      <li className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${plan.popular ? 'bg-violet-500/20' : 'bg-emerald-100'}`}>
                          <CheckIcon className={plan.popular ? 'text-violet-300' : 'text-emerald-600'} />
                        </div>
                        <span className={`text-sm ${plan.popular ? 'text-gray-300' : 'text-gray-600'}`}>
                          {tLanding('pricingFeatureUsers', { count: String(plan.userLimit) })}
                        </span>
                      </li>
                      {plan.features.map((featureKey) => (
                        <li key={featureKey} className="flex items-center gap-3">
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${plan.popular ? 'bg-violet-500/20' : 'bg-emerald-100'}`}>
                            <CheckIcon className={plan.popular ? 'text-violet-300' : 'text-emerald-600'} />
                          </div>
                          <span className={`text-sm ${plan.popular ? 'text-gray-300' : 'text-gray-600'}`}>
                            {tLanding(featureKey)}
                          </span>
                        </li>
                      ))}
                    </ul>

                    {/* Overage info */}
                    <p className={`text-xs mb-6 ${plan.popular ? 'text-gray-500' : 'text-gray-400'}`}>
                      {t('overageRate')}: {plan.overage}
                    </p>

                    {/* CTA button */}
                    {isCurrent ? (
                      <span className={`flex items-center justify-center gap-2 w-full py-4 font-medium rounded-full ${
                        plan.popular
                          ? 'bg-white text-gray-900'
                          : 'bg-violet-50 text-violet-700 border border-violet-200'
                      }`}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {t('yourPlan')}
                      </span>
                    ) : (
                      <a
                        href="mailto:info@saldora.rs"
                        className={`flex items-center justify-center w-full py-4 font-medium rounded-full transition-all duration-300 ${
                          plan.popular
                            ? 'bg-white text-gray-900 hover:bg-gray-100 hover:shadow-lg'
                            : 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:shadow-xl hover:shadow-violet-500/30 hover:scale-[1.02]'
                        }`}
                      >
                        Kontaktirajte nas
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
