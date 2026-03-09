"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ApiError } from "@/lib/api-client";
import {
  getInvitationInfo,
  acceptInvitation,
  type InvitationPublicInfo,
} from "@/lib/api/invitations";

type PageState =
  | { kind: "loading" }
  | { kind: "ready"; info: InvitationPublicInfo }
  | { kind: "expired" }
  | { kind: "accepted" }
  | { kind: "not_found" }
  | { kind: "success" };

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const t = useTranslations("auth");

  const [pageState, setPageState] = useState<PageState>({ kind: "loading" });
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadInvitation = useCallback(async () => {
    try {
      const info = await getInvitationInfo(token);
      setPageState({ kind: "ready", info });
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.status === 410) {
        setPageState({ kind: "expired" });
      } else if (apiError?.status === 409) {
        setPageState({ kind: "accepted" });
      } else if (apiError?.status === 404) {
        setPageState({ kind: "not_found" });
      } else {
        setPageState({ kind: "not_found" });
      }
    }
  }, [token]);

  useEffect(() => {
    loadInvitation();
  }, [loadInvitation]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError(t("passwordTooShort"));
      return;
    }
    if (password !== confirmPassword) {
      setError(t("passwordMismatch"));
      return;
    }

    setIsSubmitting(true);
    try {
      await acceptInvitation(token, {
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        password,
      });
      setPageState({ kind: "success" });
      setTimeout(() => {
        router.push("/login?invited=true");
      }, 2000);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.status === 410) {
        setPageState({ kind: "expired" });
      } else if (apiError?.status === 409) {
        setPageState({ kind: "accepted" });
      } else {
        setError(apiError?.message || t("serverError"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (pageState.kind === "loading") {
    return (
      <div className="text-center py-8">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-violet-600 border-r-transparent" />
        <p className="text-sm text-gray-500 mt-4">{t("loading")}</p>
      </div>
    );
  }

  if (pageState.kind === "expired") {
    return (
      <div className="text-center py-8">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <p className="text-sm text-gray-700">{t("inviteExpired")}</p>
        <Link
          href="/login"
          className="inline-block mt-4 text-sm text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          {t("login")}
        </Link>
      </div>
    );
  }

  if (pageState.kind === "accepted") {
    return (
      <div className="text-center py-8">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
          <svg className="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <p className="text-sm text-gray-700">{t("inviteAccepted")}</p>
        <Link
          href="/login"
          className="inline-block mt-4 text-sm text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          {t("login")}
        </Link>
      </div>
    );
  }

  if (pageState.kind === "not_found") {
    return (
      <div className="text-center py-8">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
          <svg className="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-gray-700">{t("inviteNotFound")}</p>
        <Link
          href="/login"
          className="inline-block mt-4 text-sm text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          {t("login")}
        </Link>
      </div>
    );
  }

  if (pageState.kind === "success") {
    return (
      <div className="text-center py-8">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <p className="text-sm text-gray-700">{t("inviteAcceptedSuccess")}</p>
      </div>
    );
  }

  const { info } = pageState;

  return (
    <>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("inviteTitle")}</h1>
        <p className="text-sm text-gray-500 mt-2">
          {t("inviteSubtitle", { orgName: info.organization_name, role: info.role })}
        </p>
      </div>

      <div className="mb-6 p-4 bg-violet-50 border border-violet-200 rounded-xl">
        <p className="text-sm text-violet-700">
          {info.email}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="firstName"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              {t("firstName")}
            </label>
            <input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Petar"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
              autoComplete="given-name"
            />
          </div>
          <div>
            <label
              htmlFor="lastName"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              {t("lastName")}
            </label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Petrovic"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
              autoComplete="family-name"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            {t("password")} <span className="text-red-500">*</span>
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t("passwordPlaceholder")}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="new-password"
          />
        </div>

        <div>
          <label
            htmlFor="confirmPassword"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            {t("confirmPassword")} <span className="text-red-500">*</span>
          </label>
          <input
            id="confirmPassword"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t("repeatPasswordPlaceholder")}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="new-password"
          />
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-violet-500/30 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
        >
          {isSubmitting ? t("acceptingInvite") : t("acceptInvite")}
        </button>
      </form>

      <p className="text-center text-sm text-gray-500 mt-6">
        {t("haveAccount")}{" "}
        <Link
          href="/login"
          className="text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          {t("login")}
        </Link>
      </p>
    </>
  );
}
