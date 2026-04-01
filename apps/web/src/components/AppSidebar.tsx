"use client";

import { useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { useSidebar } from "@/contexts/SidebarContext";
import { useNotifications } from "@/contexts/NotificationContext";
import { useClient } from "@/contexts/ClientContext";
import { useOrgPath } from "@/lib/navigation";
import { ScriptToggle } from "./ScriptToggle";

interface NavItem {
  href: string;
  labelKey:
    | "dashboard"
    | "invoices"
    | "upload"
    | "clients"
    | "rules"
    | "templates"
    | "audit"
    | "reports"
    | "billing";
  icon: React.ReactNode;
  minRole?: string;
  planBadge?: "PRO" | "AGENCY";
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
        href: "/upload",
        labelKey: "upload",
        minRole: "operator",
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
        href: "/templates",
        labelKey: "templates",
        minRole: "manager",
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
        minRole: "admin",
        planBadge: "PRO",
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
      {
        href: "/izvestaji",
        labelKey: "reports",
        minRole: "operator",
        planBadge: "PRO",
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
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        ),
      },
      {
        href: "/clients",
        labelKey: "clients",
        minRole: "operator",
        planBadge: "AGENCY",
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
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
        ),
      },
      {
        href: "/rules",
        labelKey: "rules",
        minRole: "manager",
        planBadge: "AGENCY",
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
  const { user, logout, hasRole } = useAuth();
  const { isCollapsed, isMobileOpen, toggleCollapse, openMobile, closeMobile } =
    useSidebar();
  const t = useTranslations("nav");
  const { pendingJoinRequests } = useNotifications();
  const { clients, selectedClientId, selectClient, isAgency } = useClient();
  const orgPath = useOrgPath();

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
    badge?: number,
    planBadge?: "PRO" | "AGENCY",
  ) {
    const active = isActive(href);
    return (
      <Link
        key={href}
        href={href}
        onClick={mobile ? closeMobile : undefined}
        title={collapsed ? label : undefined}
        className={`group flex items-center ${collapsed ? "justify-center" : ""} ${mobile ? "gap-3.5 px-5 py-3 text-[15px]" : "gap-3 px-3 py-2.5 text-sm"} ${mobile ? "rounded-lg" : "rounded-xl"} font-medium transition-all duration-200 relative ${
          active
            ? mobile
              ? "bg-violet-50 text-violet-700 border-l-[3px] border-violet-600 pl-[17px]"
              : "bg-violet-50 text-violet-700"
            : mobile
              ? "text-gray-700 hover:bg-gray-50 active:bg-gray-100"
              : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
        }`}
      >
        {active && !mobile && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-violet-600 rounded-r-full" />
        )}
        <span
          className={`shrink-0 relative ${mobile ? "[&>svg]:w-6 [&>svg]:h-6" : ""} ${active ? "text-violet-600" : mobile ? "text-gray-500" : "text-gray-400 group-hover:text-gray-600"}`}
        >
          {icon}
          {collapsed && badge ? (
            <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full">
              {badge}
            </span>
          ) : null}
        </span>
        {!collapsed && label}
        {!collapsed && planBadge && (
          <span className="ml-auto px-1.5 py-0.5 text-[10px] font-semibold rounded bg-violet-100 text-violet-600">
            {planBadge}
          </span>
        )}
        {!collapsed && !planBadge && badge ? (
          <span className="ml-auto min-w-[20px] h-5 px-1.5 flex items-center justify-center bg-red-500 text-white text-[11px] font-bold rounded-full">
            {badge}
          </span>
        ) : null}
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
              href={orgPath("/dashboard")}
              className="flex items-center justify-center py-2"
            >
              {collapsed ? (
                <Image src="/app-icon.png" alt="Saldora" width={40} height={40} className="rounded-lg" />
              ) : (
                <Image src="/logo-text-only.png" alt="Saldora" width={150} height={40} className="object-contain" />
              )}
            </Link>
          </div>
        )}

        {/* Client selector (Agency only) */}
        {isAgency && !collapsed && !mobile && clients.length > 0 && (
          <div className="px-3 py-2 border-b border-gray-100">
            <select
              value={selectedClientId || ""}
              onChange={(e) => selectClient(e.target.value || null)}
              className="w-full px-2.5 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 truncate"
            >
              <option value="">{t("allClients")}</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Main nav links */}
        <nav className={`flex-1 overflow-y-auto ${mobile ? "py-2" : "px-2 py-4"}`}>
          {NAV_GROUPS.map((group, gi) => {
            const visibleItems = group.items.filter(
              (item) => !item.minRole || hasRole(item.minRole),
            );
            if (visibleItems.length === 0) return null;
            return (
            <div key={group.labelKey} className={mobile ? `${gi > 0 ? "border-t border-gray-200 mt-2 pt-2" : ""}` : `${gi > 0 ? "mt-4" : ""}`}>
              {!collapsed && (
                <p className={`${mobile ? "px-5 pt-3 pb-1 text-[13px]" : "px-3 mb-1 text-[11px]"} font-semibold text-gray-400 uppercase tracking-wider`}>
                  {t(group.labelKey)}
                </p>
              )}
              <div className={mobile ? "space-y-0.5 px-2" : "space-y-1"}>
                {visibleItems.map((item) =>
                  renderNavLink(
                    orgPath(item.href),
                    item.icon,
                    t(item.labelKey),
                    collapsed,
                    mobile,
                    undefined,
                    item.planBadge,
                  ),
                )}
              </div>
            </div>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className={`${mobile ? "px-2 pb-4 space-y-0.5" : "px-2 pb-4 space-y-2"} border-t ${mobile ? "border-gray-200" : "border-gray-100"} pt-2`}>
          {/* Billing */}
          {hasRole("admin") && renderNavLink(
            orgPath("/billing"),
            BILLING_ICON,
            t("billing"),
            collapsed,
            mobile,
          )}

          {/* Settings */}
          {renderNavLink(
            orgPath("/settings"),
            SETTINGS_ICON,
            t("settings"),
            collapsed,
            mobile,
            pendingJoinRequests || undefined,
          )}

          {/* Script toggle */}
          <div className={collapsed ? "flex justify-center" : mobile ? "px-5 py-2" : "px-3"}>
            <ScriptToggle collapsed={collapsed} />
          </div>

          {/* User section */}
          <div
            className={`${collapsed ? "px-1" : mobile ? "mx-3 px-4 py-3 bg-gray-50 rounded-xl" : "px-3"} pt-2 border-t ${mobile ? "border-gray-200" : "border-gray-100"}`}
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
                <div className={`flex items-center gap-3 mb-2 ${mobile ? "flex-col text-center" : ""}`}>
                  <div className={`${mobile ? "w-12 h-12 text-base" : "w-8 h-8 text-xs"} bg-gradient-to-br from-violet-500 to-indigo-500 rounded-full flex items-center justify-center text-white font-semibold shrink-0`}>
                    {userInitials}
                  </div>
                  <div className={`min-w-0 ${mobile ? "" : "flex-1"}`}>
                    <p className={`${mobile ? "text-[15px]" : "text-sm"} font-medium text-gray-900 truncate`}>
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
                  className={`w-full flex items-center ${mobile ? "justify-center gap-3 py-2.5 text-[15px]" : "gap-2 px-2 py-2 text-sm"} text-gray-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors`}
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
        <Link href={orgPath("/dashboard")} className="flex-1 flex items-center justify-center">
          <Image src="/logo-text-only.png" alt="Saldora" width={120} height={32} className="object-contain" />
        </Link>
        <div className="w-10" />
      </div>

      {/* Mobile full-screen overlay */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-white flex flex-col">
          {/* Close button */}
          <div className="flex items-center justify-between px-4 h-14 border-b border-gray-100 shrink-0">
            <Link href={orgPath("/dashboard")} onClick={closeMobile}>
              <Image src="/logo-text-only.png" alt="Saldora" width={120} height={32} className="object-contain" />
            </Link>
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
