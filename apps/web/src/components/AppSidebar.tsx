"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { useSidebar } from "@/contexts/SidebarContext";
import { ScriptToggle } from "./ScriptToggle";

interface NavItem {
  href: string;
  labelKey: "dashboard" | "invoices" | "sefInbox" | "upload";
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    labelKey: "dashboard",
    icon: (
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1h-2z"
        />
      </svg>
    ),
  },
  {
    href: "/invoices",
    labelKey: "invoices",
    icon: (
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
  {
    href: "/sef-inbox",
    labelKey: "sefInbox",
    icon: (
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
        />
      </svg>
    ),
  },
  {
    href: "/upload",
    labelKey: "upload",
    icon: (
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
        />
      </svg>
    ),
  },
];

const SETTINGS_ICON = (
  <svg
    className="w-5 h-5"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.75}
      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
    />
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.75}
      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
    />
  </svg>
);

/**
 * Collapsible sidebar navigation for authenticated app pages.
 *
 * Desktop: 240px expanded, 64px collapsed, with smooth transition.
 * Mobile: slim top bar with hamburger → overlay from left.
 * Collapse state managed via SidebarContext and persisted in localStorage.
 */
export function AppSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { isCollapsed, isMobileOpen, toggleCollapse, openMobile, closeMobile } =
    useSidebar();
  const t = useTranslations("nav");

  // Close mobile menu on route change
  useEffect(() => {
    closeMobile();
  }, [pathname, closeMobile]);

  const userInitials = user
    ? `${user.firstName?.[0] ?? ""}${user.lastName?.[0] ?? ""}`.toUpperCase() ||
      user.email[0].toUpperCase()
    : "?";

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  function renderNavLink(
    href: string,
    icon: React.ReactNode,
    label: string,
    collapsed: boolean,
    mobile: boolean,
  ) {
    const active = isActive(href);
    return (
      <Link
        key={href}
        href={href}
        onClick={mobile ? closeMobile : undefined}
        title={collapsed ? label : undefined}
        className={`group flex items-center ${collapsed ? "justify-center" : ""} gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 relative ${
          active
            ? "bg-violet-50 text-violet-700"
            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
        }`}
      >
        {active && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-violet-600 rounded-r-full" />
        )}
        <span
          className={`shrink-0 ${active ? "text-violet-600" : "text-gray-400 group-hover:text-gray-600"}`}
        >
          {icon}
        </span>
        {!collapsed && label}
      </Link>
    );
  }

  function renderSidebarContent(mobile: boolean) {
    const collapsed = mobile ? false : isCollapsed;

    return (
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div
          className={`flex items-center justify-center shrink-0 ${collapsed ? "px-2" : "px-4"} h-16 border-b border-gray-100`}
        >
          <Link
            href="/dashboard"
            className="flex items-center justify-center py-2"
            onClick={mobile ? closeMobile : undefined}
          >
            {collapsed ? (
              <span className="text-xl font-bold gradient-text">F</span>
            ) : (
              <span className="text-lg font-bold gradient-text">FakturaAI</span>
            )}
          </Link>
        </div>

        {/* Main nav links */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) =>
            renderNavLink(
              item.href,
              item.icon,
              t(item.labelKey),
              collapsed,
              mobile,
            ),
          )}
        </nav>

        {/* Bottom section */}
        <div className="px-2 pb-4 space-y-2 border-t border-gray-100 pt-3">
          {/* Settings */}
          {renderNavLink(
            "/settings",
            SETTINGS_ICON,
            t("settings"),
            collapsed,
            mobile,
          )}

          {/* Script toggle */}
          <div className={collapsed ? "flex justify-center" : "px-3"}>
            <ScriptToggle collapsed={collapsed} />
          </div>

          {/* User section */}
          <div
            className={`${collapsed ? "px-1" : "px-3"} pt-2 border-t border-gray-100`}
          >
            {collapsed ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-semibold">
                  {userInitials}
                </div>
                <button
                  onClick={logout}
                  className="w-10 h-10 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                  title={t("logout")}
                  aria-label={t("logout")}
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.75}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0">
                    {userInitials}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {user?.firstName} {user?.lastName}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {user?.email}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (mobile) closeMobile();
                    logout();
                  }}
                  className="w-full flex items-center gap-2 px-2 py-2 text-sm text-gray-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.75}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  {t("logout")}
                </button>
              </>
            )}
          </div>

          {/* Collapse toggle (desktop only) */}
          {!mobile && (
            <button
              onClick={toggleCollapse}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
              aria-label={isCollapsed ? t("expand") : t("collapse")}
            >
              <svg
                className={`w-4 h-4 transition-transform duration-300 ${isCollapsed ? "rotate-180" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                />
              </svg>
              {!isCollapsed && t("collapse")}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-14 bg-white/80 backdrop-blur-lg border-b border-gray-200/50 z-40 flex items-center px-4">
        <button
          onClick={openMobile}
          className="p-2 -ml-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors"
          aria-label={t("openMenu")}
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
        <Link href="/dashboard" className="flex items-center mx-auto">
          <span className="text-base font-bold gradient-text">FakturaAI</span>
        </Link>
        <div className="w-10" />
      </div>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            onClick={closeMobile}
          />
          <div className="absolute left-0 top-0 bottom-0 w-[280px] bg-white shadow-2xl">
            <button
              onClick={closeMobile}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors z-10"
              aria-label={t("closeMenu")}
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            {renderSidebarContent(true)}
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex flex-col fixed left-0 top-0 bottom-0 bg-white border-r border-gray-200/60 z-30 transition-all duration-300 ease-in-out ${
          isCollapsed ? "w-16" : "w-60"
        }`}
      >
        {renderSidebarContent(false)}
      </aside>
    </>
  );
}
