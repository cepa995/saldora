'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard } from '@/hooks/useDashboard';
import { StatusBadge } from '@/components/StatusBadge';
import { formatAmountSr, formatRelativeTime } from '@/lib/formatters';
import type { InvoiceResponse } from '@/lib/types/invoice';

/* -- Inline SVG Icons --------------------------------------------------- */

function DocumentStackIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function BoltIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

function EyeIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  );
}

function CheckCircleIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function UploadIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    </svg>
  );
}

function ListIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  );
}

function DownloadIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  );
}

function ArrowRightIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
    </svg>
  );
}

/* -- Stat Card ---------------------------------------------------------- */

interface StatCardProps {
  icon: React.ReactNode;
  iconBg: string;
  count: number;
  label: string;
}

function StatCard({ icon, iconBg, count, label }: StatCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm hover-lift cursor-default transition-all duration-200">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg}`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-900 mt-3 tabular-nums">{count}</p>
      <p className="text-sm text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}

/* -- Skeleton Components ------------------------------------------------ */

function StatCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <div className="w-10 h-10 rounded-xl bg-gray-200 animate-pulse" />
      <div className="h-8 w-16 bg-gray-200 rounded-lg animate-pulse mt-3" />
      <div className="h-4 w-24 bg-gray-100 rounded animate-pulse mt-2" />
    </div>
  );
}

function RecentInvoiceRowSkeleton() {
  return (
    <div className="px-5 sm:px-6 py-3.5 border-b border-gray-50">
      {/* Desktop */}
      <div className="hidden sm:grid grid-cols-[minmax(80px,auto)_1fr_auto_auto_auto] items-center gap-4">
        <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
        <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
        <div className="h-6 w-20 bg-gray-200 rounded-full animate-pulse" />
        <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
        <div className="h-4 w-16 bg-gray-100 rounded animate-pulse" />
      </div>
      {/* Mobile */}
      <div className="sm:hidden space-y-2">
        <div className="flex items-center justify-between">
          <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
          <div className="h-6 w-16 bg-gray-200 rounded-full animate-pulse" />
        </div>
        <div className="h-4 w-36 bg-gray-100 rounded animate-pulse" />
        <div className="flex items-center justify-between">
          <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
          <div className="h-3 w-12 bg-gray-100 rounded animate-pulse" />
        </div>
      </div>
    </div>
  );
}

/* -- Recent Invoice Row ------------------------------------------------- */

function RecentInvoiceRow({ invoice }: { invoice: InvoiceResponse }) {
  return (
    <Link
      href={`/invoices/${invoice.id}`}
      className="block px-5 sm:px-6 py-3.5 border-b border-gray-100 sm:border-gray-50 hover:bg-violet-50/30 transition-colors group"
    >
      {/* Desktop row */}
      <div className="hidden sm:grid grid-cols-[minmax(80px,auto)_1fr_auto_auto_auto] items-center gap-4">
        <span className="text-sm font-medium text-gray-900 truncate">
          {invoice.invoice_number ?? '—'}
        </span>
        <span className="text-sm text-gray-600 truncate min-w-0">
          {invoice.seller?.name ?? '—'}
        </span>
        <StatusBadge status={invoice.status} />
        <span className="text-sm font-semibold text-gray-900 tabular-nums text-right whitespace-nowrap">
          {formatAmountSr(invoice.total_amount, invoice.currency)}
        </span>
        <span className="text-xs text-gray-500 text-right whitespace-nowrap">
          {formatRelativeTime(invoice.created_at)}
        </span>
      </div>
      {/* Mobile card */}
      <div className="sm:hidden space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-gray-900 truncate">
            {invoice.invoice_number ?? '—'}
          </span>
          <StatusBadge status={invoice.status} />
        </div>
        <p className="text-sm text-gray-500 truncate">{invoice.seller?.name ?? '—'}</p>
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-gray-900 tabular-nums">
            {formatAmountSr(invoice.total_amount, invoice.currency)}
          </span>
          <span className="text-xs text-gray-400">
            {formatRelativeTime(invoice.created_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}

/* -- Dashboard Page ----------------------------------------------------- */

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, error, refresh } = useDashboard();
  const t = useTranslations('dashboard');
  const tCommon = useTranslations('common');

  return (
    <div>
      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {t('welcome', { name: user?.firstName ?? 'korisniče' })}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('overview')}</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button
            onClick={refresh}
            className="text-sm font-medium text-red-700 hover:text-red-900 transition-colors px-3 py-1 rounded-lg hover:bg-red-100"
          >
            {tCommon('retry')}
          </button>
        </div>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : data ? (
          <>
            <StatCard
              icon={<DocumentStackIcon className="w-5 h-5 text-violet-600" />}
              iconBg="bg-violet-100"
              count={data.totalCount}
              label={t('totalInvoices')}
            />
            <StatCard
              icon={<BoltIcon className="w-5 h-5 text-amber-600" />}
              iconBg="bg-amber-100"
              count={data.processingCount}
              label={t('processing')}
            />
            <StatCard
              icon={<EyeIcon className="w-5 h-5 text-blue-600" />}
              iconBg="bg-blue-100"
              count={data.reviewCount}
              label={t('inReview')}
            />
            <StatCard
              icon={<CheckCircleIcon className="w-5 h-5 text-green-600" />}
              iconBg="bg-green-100"
              count={data.verifiedCount}
              label={t('verified')}
            />
          </>
        ) : null}
      </div>

      {/* Recent invoices + Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        {/* Recent invoices */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">{t('recentInvoices')}</h2>
            {data && data.totalCount > 0 && (
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full tabular-nums">
                {data.totalCount}
              </span>
            )}
          </div>

          <div>
            {isLoading ? (
              <>
                <RecentInvoiceRowSkeleton />
                <RecentInvoiceRowSkeleton />
                <RecentInvoiceRowSkeleton />
                <RecentInvoiceRowSkeleton />
                <RecentInvoiceRowSkeleton />
              </>
            ) : data && data.recentInvoices.length > 0 ? (
              data.recentInvoices.map((invoice) => (
                <RecentInvoiceRow key={invoice.id} invoice={invoice} />
              ))
            ) : (
              <div className="py-12 text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <DocumentStackIcon className="w-6 h-6 text-gray-400" />
                </div>
                <p className="text-sm font-medium text-gray-900">{t('noInvoices')}</p>
                <p className="text-xs text-gray-500 mt-1">{t('noInvoicesSubtitle')}</p>
                <Link
                  href="/upload"
                  className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors"
                >
                  <UploadIcon className="w-4 h-4" />
                  {t('uploadInvoice')}
                </Link>
              </div>
            )}
          </div>

          {data && data.recentInvoices.length > 0 && (
            <div className="px-6 py-3 border-t border-gray-100 bg-gray-50/50">
              <Link
                href="/invoices"
                className="text-sm text-violet-600 hover:text-violet-700 font-medium inline-flex items-center gap-1.5 transition-colors group"
              >
                {t('viewAllInvoices')}
                <ArrowRightIcon className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h2 className="font-semibold text-gray-900 mb-4">{t('quickActions')}</h2>

          <div className="space-y-3">
            <Link
              href="/upload"
              className="flex items-center gap-3 w-full px-4 py-3 rounded-xl font-medium text-sm bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:shadow-lg hover:shadow-violet-500/25 hover:scale-[1.02] transition-all duration-200"
            >
              <UploadIcon className="w-5 h-5" />
              {t('uploadInvoice')}
            </Link>

            <Link
              href="/invoices"
              className="flex items-center gap-3 w-full px-4 py-3 rounded-xl font-medium text-sm bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <ListIcon className="w-5 h-5 text-gray-500" />
              {t('viewAllInvoices')}
            </Link>

            <Link
              href="/invoices"
              className="flex items-center gap-3 w-full px-4 py-3 rounded-xl font-medium text-sm bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <DownloadIcon className="w-5 h-5 text-gray-500" />
              {t('exportReport')}
            </Link>
          </div>

          {/* Quick tip */}
          <div className="mt-6 p-4 bg-violet-50 rounded-xl border border-violet-100">
            <p className="text-xs text-violet-700 font-medium mb-1">{t('quickTip')}</p>
            <p className="text-xs text-violet-600">{t('quickTipText')}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
