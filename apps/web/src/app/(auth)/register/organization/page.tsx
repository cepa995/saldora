"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import {
  type OrganizationSearchResult,
  searchOrganizations,
  submitJoinRequest,
  getMyPendingRequest,
} from "@/lib/api/join-requests";
import type { ApiError } from "@/lib/api-client";
import { validatePib } from "@/lib/validate-pib";

type Tab = "create" | "join";

export default function OrganizationSetupPage() {
  const { user, isLoading, isAuthenticated, createOrganization } = useAuth();
  const router = useRouter();
  const t = useTranslations("auth");

  const [activeTab, setActiveTab] = useState<Tab>("create");
  const [pendingOrgName, setPendingOrgName] = useState<string | null>(null);
  const shouldCheck = !isLoading && isAuthenticated && !user?.organizationId;
  const [checkingPending, setCheckingPending] = useState(true);

  // Check for existing pending join request
  useEffect(() => {
    if (!shouldCheck) return;
    getMyPendingRequest()
      .then((req) => {
        if (req) setPendingOrgName(req.organization_name ?? "");
      })
      .catch(() => {})
      .finally(() => setCheckingPending(false));
  }, [shouldCheck]);

  // Redirect if user already has an org
  useEffect(() => {
    if (!isLoading && isAuthenticated && user?.organizationId) {
      if (user?.orgSlug) {
        router.push(`/${user.orgSlug}/dashboard`);
      }
    }
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, user?.organizationId, user?.orgSlug, router]);

  const stepIndicator = (
    <div className="flex items-center justify-center gap-2 mb-8">
      <span className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-full bg-green-50 text-green-600 text-sm font-medium min-w-[140px]">
        <span className="w-5 h-5 rounded-full bg-green-500 text-white flex items-center justify-center shrink-0">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </span>
        {t("stepAccount")}
      </span>
      <svg className="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
      <span className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-full bg-violet-100 text-violet-700 text-sm font-medium min-w-[140px]">
        <span className="w-5 h-5 rounded-full bg-violet-600 text-white flex items-center justify-center text-xs font-bold shrink-0">2</span>
        {t("stepOrganization")}
      </span>
    </div>
  );

  if (isLoading || !isAuthenticated || checkingPending) {
    return (
      <>
        {stepIndicator}
        <div className="flex items-center justify-center py-12">
          <svg
            className="animate-spin h-8 w-8 text-violet-600"
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
        </div>
      </>
    );
  }

  // User has a pending join request — show waiting state, no tabs
  if (pendingOrgName !== null) {
    return (
      <>
        {stepIndicator}
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            {t("waitingApproval")}
          </h2>
          <p className="text-sm text-gray-500">
            {t("waitingApprovalDesc", { orgName: pendingOrgName })}
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      {stepIndicator}

      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {t("setupOrganization")}
        </h1>
        <p className="text-sm text-gray-500 mt-2">
          {t("setupOrgSubtitle")}
        </p>
      </div>

      {/* Tab selector */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-6">
        <button
          type="button"
          onClick={() => setActiveTab("create")}
          className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all ${
            activeTab === "create"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {t("createOrg")}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("join")}
          className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all ${
            activeTab === "join"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {t("joinOrg")}
        </button>
      </div>

      {activeTab === "create" ? (
        <CreateOrganizationForm onSubmit={createOrganization} />
      ) : (
        <JoinOrganizationForm />
      )}
    </>
  );
}

function CreateOrganizationForm({
  onSubmit,
}: {
  onSubmit: (name: string, pib?: string) => Promise<void>;
}) {
  const t = useTranslations("auth");
  const [name, setName] = useState("");
  const [pib, setPib] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pibError, setPibError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handlePibChange(value: string) {
    setPib(value);
    setPibError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (pib.trim()) {
      const validationKey = validatePib(pib);
      if (validationKey) {
        setPibError(t(validationKey));
        return;
      }
    }

    setIsSubmitting(true);
    try {
      await onSubmit(name, pib || undefined);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError?.message || t("serverError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label
          htmlFor="orgName"
          className="block text-sm font-medium text-gray-700 mb-1.5"
        >
          {t("orgName")} <span className="text-red-500">*</span>
        </label>
        <input
          id="orgName"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("orgNamePlaceholder")}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
          autoComplete="organization"
        />
      </div>

      <div>
        <label
          htmlFor="pib"
          className="block text-sm font-medium text-gray-700 mb-1.5"
        >
          {t("orgPib")}
        </label>
        <input
          id="pib"
          type="text"
          value={pib}
          onChange={(e) => handlePibChange(e.target.value)}
          placeholder="123456789"
          maxLength={9}
          className={`w-full px-4 py-3 border rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:border-transparent transition-all ${
            pibError
              ? "border-red-300 focus:ring-red-500"
              : "border-gray-300 focus:ring-violet-500"
          }`}
        />
        {pibError && (
          <p className="text-xs text-red-600 mt-1">{pibError}</p>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting || !name.trim()}
        className="w-full py-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-violet-500/30 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
      >
        {isSubmitting ? t("creating") : t("createOrgButton")}
      </button>
    </form>
  );
}

function JoinOrganizationForm() {
  const t = useTranslations("auth");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<OrganizationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<OrganizationSearchResult | null>(null);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 3) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const data = await searchOrganizations(q);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => doSearch(query), 300);
    return () => clearTimeout(timer);
  }, [query, doSearch]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedOrg) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await submitJoinRequest(selectedOrg.id, message || undefined);
      // Reload the page so the page-level pending check picks up the new request
      window.location.reload();
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.status === 409) {
        setError(t("alreadyRequested"));
      } else {
        setError(apiError?.message || t("serverError"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label
          htmlFor="search"
          className="block text-sm font-medium text-gray-700 mb-1.5"
        >
          {t("searchOrg")}
        </label>
        <input
          id="search"
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedOrg(null);
          }}
          placeholder={t("searchOrgPlaceholder")}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
        />
        {query.length > 0 && query.length < 3 && (
          <p className="text-xs text-gray-400 mt-1">{t("searchMinChars")}</p>
        )}
      </div>

      {/* Search results */}
      {query.length >= 3 && !selectedOrg && (
        <div className="border border-gray-200 rounded-xl overflow-hidden">
          {isSearching ? (
            <div className="p-4 text-center text-sm text-gray-500">
              {t("searching")}
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-sm text-gray-500">
              {t("noOrgsFound")}
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {results.map((org) => (
                <li key={org.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedOrg(org)}
                    className="w-full text-left px-4 py-3 hover:bg-violet-50 transition-colors"
                  >
                    <span className="font-medium text-gray-900">{org.name}</span>
                    <span className="text-sm text-gray-400 ml-2">/{org.slug}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Selected organization */}
      {selectedOrg && (
        <div className="p-4 bg-violet-50 border border-violet-200 rounded-xl flex items-center justify-between">
          <div>
            <span className="font-medium text-violet-900">{selectedOrg.name}</span>
            <span className="text-sm text-violet-500 ml-2">/{selectedOrg.slug}</span>
          </div>
          <button
            type="button"
            onClick={() => setSelectedOrg(null)}
            className="text-violet-600 hover:text-violet-800 text-sm"
          >
            {t("change")}
          </button>
        </div>
      )}

      {selectedOrg && (
        <div>
          <label
            htmlFor="joinMessage"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            {t("joinMessage")}
          </label>
          <textarea
            id="joinMessage"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t("joinMessagePlaceholder")}
            maxLength={500}
            rows={3}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all resize-none"
          />
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting || !selectedOrg}
        className="w-full py-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-violet-500/30 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
      >
        {isSubmitting ? t("submitting") : t("submitJoinRequest")}
      </button>
    </form>
  );
}
