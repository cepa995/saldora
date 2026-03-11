'use client';

import { useTranslations } from 'next-intl';
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { AppSidebar } from '@/components/AppSidebar';

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const { isCollapsed } = useSidebar();
  const t = useTranslations('common');

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-violet-600 focus:text-white focus:rounded-lg"
      >
        {t('skipToContent')}
      </a>

      <AppSidebar />

      <div
        className={`min-h-screen flex flex-col pt-14 md:pt-0 transition-all duration-300 ${
          isCollapsed ? 'md:ml-16' : 'md:ml-60'
        }`}
      >
        <main id="main-content" className="flex-1 w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-gray-100 mt-auto">
          <div className="px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-sm text-gray-500">
              {t('copyright', { year: new Date().getFullYear().toString() })}
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}

/**
 * Shared layout for all authenticated app pages.
 *
 * Provides sidebar context, notification context, sidebar navigation,
 * main content area, and footer. Auth guard lives in [orgSlug]/layout.tsx.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <NotificationProvider>
        <AppLayoutInner>{children}</AppLayoutInner>
      </NotificationProvider>
    </SidebarProvider>
  );
}
