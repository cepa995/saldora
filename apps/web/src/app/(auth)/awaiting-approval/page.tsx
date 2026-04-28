"use client";

/**
 * Landing page shown to authenticated users whose org is not yet
 * approved (subscription_status not in {active, trial}).
 *
 * The page polls the JWT refresh endpoint when the user clicks
 * "Check status" — that endpoint re-reads the org's current
 * subscription_status, so the new claim flips as soon as the admin
 * runs the approval script. When approved we redirect to the dashboard.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { useAuth } from "@/contexts/AuthContext";
import {
  extractUserFromToken,
  isSubscriptionApproved,
  refreshAccessToken,
} from "@/lib/auth";

export default function AwaitingApprovalPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const t = useTranslations("awaitingApproval");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [checking, setChecking] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Send the user away from this page if they don't belong here.
  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (!user?.organizationId) {
      router.replace("/register/organization");
      return;
    }
    if (
      isSubscriptionApproved(user.subscriptionStatus) &&
      user.orgSlug
    ) {
      router.replace(`/${user.orgSlug}/dashboard`);
    }
  }, [isLoading, isAuthenticated, user, router]);

  async function handleCheckStatus() {
    setChecking(true);
    setFeedback(null);
    try {
      const token = await refreshAccessToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      const refreshed = extractUserFromToken(token);
      if (
        refreshed &&
        isSubscriptionApproved(refreshed.subscriptionStatus) &&
        refreshed.orgSlug
      ) {
        router.replace(`/${refreshed.orgSlug}/dashboard`);
        return;
      }
      setFeedback(t("stillPending"));
    } finally {
      setChecking(false);
    }
  }

  if (isLoading || !user || !user.organizationId) {
    return (
      <p className="text-center text-sm text-gray-500">
        {tCommon("loading")}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-14 h-14 mx-auto rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mb-4">
          <svg
            className="w-7 h-7"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.75}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 8v4l2.5 2.5M12 21a9 9 0 110-18 9 9 0 010 18z"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="text-sm text-gray-500 mt-2 leading-relaxed">
          {t("subtitle")}
        </p>
      </div>

      {!user.emailVerified && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-semibold">{t("emailNotVerifiedTitle")}</p>
          <p className="mt-1 leading-relaxed">{t("emailNotVerifiedBody")}</p>
        </div>
      )}

      <div className="rounded-lg border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-600 flex items-center justify-between gap-3">
        <span className="font-medium text-stone-500">{t("orgLabel")}</span>
        <span className="font-semibold text-stone-900 truncate">
          {user.email}
        </span>
      </div>

      {feedback && (
        <p className="text-center text-sm text-stone-600">{feedback}</p>
      )}

      <button
        type="button"
        onClick={handleCheckStatus}
        disabled={checking}
        className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm shadow-violet-600/10"
      >
        {checking && (
          <svg
            className="animate-spin h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {checking ? t("checking") : t("checkStatus")}
      </button>

      <button
        type="button"
        onClick={() => logout()}
        className="w-full text-center text-sm text-stone-500 hover:text-stone-800 underline-offset-4 hover:underline"
      >
        {t("logout")}
      </button>
    </div>
  );
}
