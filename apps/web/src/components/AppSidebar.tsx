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
  labelKey:
    | "dashboard"
    | "invoices"
    | "sefInbox"
    | "upload"
    | "rules"
    | "templates"
    | "audit"
    | "billing";
  icon: React.ReactNode;
}

interface NavGroup {
  labelKey: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: "groupOverview",
    items: [
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
    ],
  },
  {
    labelKey: "groupDocuments",
    items: [
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
    ],
  },
  {
    labelKey: "groupTools",
    items: [
      {
        href: "/rules",
        labelKey: "rules",
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        ),
      },
      {
        href: "/templates",
        labelKey: "templates",
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
              d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M10.875 12c-.621 0-1.125.504-1.125 1.125M12 12c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125M12 15.375c0-.621-.504-1.125-1.125-1.125"
            />
          </svg>
        ),
      },
      {
        href: "/revizija",
        labelKey: "audit",
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
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
            />
          </svg>
        ),
      },
    ],
  },
];

const BILLING_ICON = (
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
      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
    />
  </svg>
);

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
        className={`group flex items-center ${collapsed ? "justify-center" : ""} ${mobile ? "justify-center gap-4 px-4 py-3.5 text-base" : "gap-3 px-3 py-2.5 text-sm"} rounded-xl font-medium transition-all duration-200 relative ${
          active
            ? "bg-violet-50 text-violet-700"
            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
        }`}
      >
        {active && !mobile && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-violet-600 rounded-r-full" />
        )}
        <span
          className={`shrink-0 ${mobile ? "[&>svg]:w-6 [&>svg]:h-6" : ""} ${active ? "text-violet-600" : "text-gray-400 group-hover:text-gray-600"}`}
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
        {/* Logo — only on desktop sidebar */}
        {!mobile && (
          <div
            className={`flex items-center justify-center shrink-0 ${collapsed ? "px-2" : "px-4"} h-16 border-b border-gray-100`}
          >
            <Link
              href="/dashboard"
              className="flex items-center justify-center py-2"
            >
              {collapsed ? (
                <span className="text-xl font-bold gradient-text">F</span>
              ) : (
                <span className="text-lg font-bold gradient-text">FakturaAI</span>
              )}
            </Link>
          </div>
        )}

        {/* Main nav links */}
        <nav className={`flex-1 overflow-y-auto ${mobile ? "px-6 py-6 flex flex-col justify-center" : "px-2 py-4"}`}>
          {NAV_GROUPS.map((group, gi) => (
            <div key={group.labelKey} className={gi > 0 ? (mobile ? "mt-6" : "mt-4") : ""}>
              {!collapsed && (
                <p className={`${mobile ? "text-center mb-2 text-xs" : "px-3 mb-1 text-[11px]"} font-semibold text-gray-400 uppercase tracking-wider`}>
                  {t(group.labelKey)}
                </p>
              )}
              <div className={mobile ? "space-y-1.5" : "space-y-1"}>
                {group.items.map((item) =>
                  renderNavLink(
                    item.href,
                    item.icon,
                    t(item.labelKey),
                    collapsed,
                    mobile,
                  ),
                )}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom section */}
        <div className={`${mobile ? "px-6 pb-6 space-y-2" : "px-2 pb-4 space-y-2"} border-t border-gray-100 pt-3`}>
          {/* Billing */}
          {renderNavLink(
            "/billing",
            BILLING_ICON,
            t("billing"),
            collapsed,
            mobile,
          )}

          {/* Settings */}
          {renderNavLink(
            "/settings",
            SETTINGS_ICON,
            t("settings"),
            collapsed,
            mobile,
          )}

          {/* Script toggle */}
          <div className={collapsed ? "flex justify-center" : mobile ? "flex justify-center px-4 py-2" : "px-3"}>
            <ScriptToggle collapsed={collapsed} />
          </div>

          {/* User section */}
          <div
            className={`${collapsed ? "px-1" : mobile ? "px-4" : "px-3"} pt-2 border-t border-gray-100`}
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
                <div className={`flex items-center gap-3 mb-2 ${mobile ? "justify-center" : ""}`}>
                  <div className={`${mobile ? "w-10 h-10 text-sm" : "w-8 h-8 text-xs"} bg-gradient-to-br from-violet-500 to-indigo-500 rounded-full flex items-center justify-center text-white font-semibold shrink-0`}>
                    {userInitials}
                  </div>
                  <div className="min-w-0">
                    <p className={`${mobile ? "text-base" : "text-sm"} font-medium text-gray-900 truncate`}>
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
                  className={`w-full flex items-center ${mobile ? "justify-center gap-3 py-3 text-base" : "gap-2 px-2 py-2 text-sm"} text-gray-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors`}
                >
                  <svg
                    className={mobile ? "w-5 h-5" : "w-4 h-4"}
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

      {/* Mobile full-screen overlay */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-white flex flex-col">
          {/* Close button */}
          <div className="flex items-center justify-between px-4 h-14 border-b border-gray-100 shrink-0">
            <span className="text-lg font-bold gradient-text">FakturaAI</span>
            <button
              onClick={closeMobile}
              className="p-2 -mr-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              aria-label={t("closeMenu")}
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          {renderSidebarContent(true)}
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
