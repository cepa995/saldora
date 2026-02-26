"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import type { ApiError } from "@/lib/api-client";

function useErrorMessage() {
  const t = useTranslations("auth");
  return (error: unknown): string => {
    const apiError = error as ApiError;
    if (apiError?.status === 401) return t("invalidCredentials");
    if (apiError?.status === 422) return t("invalidData");
    return t("serverError");
  };
}

function RegistrationBanner() {
  const searchParams = useSearchParams();
  const t = useTranslations("auth");
  if (searchParams.get("registered") !== "true") return null;
  return (
    <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl">
      <p className="text-sm text-green-700">{t("registrationSuccess")}</p>
    </div>
  );
}

export default function LoginPage() {
  const { login } = useAuth();
  const t = useTranslations("auth");
  const getErrorMessage = useErrorMessage();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("loginTitle")}</h1>
        <p className="text-sm text-gray-500 mt-2">{t("loginSubtitle")}</p>
      </div>

      <Suspense>
        <RegistrationBanner />
      </Suspense>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            {t("email")}
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t("emailPlaceholder")}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="email"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            {t("password")}
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t("passwordPlaceholder")}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="current-password"
          />
          <div className="flex justify-end mt-1.5">
            <Link
              href="/password-reset"
              className="text-sm text-violet-600 hover:text-violet-700 transition-colors"
            >
              {t("forgotPassword")}
            </Link>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-violet-500/30 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
        >
          {isLoading ? t("loggingIn") : t("login")}
        </button>
      </form>

      <p className="text-center text-sm text-gray-500 mt-6">
        {t("noAccount")}{" "}
        <Link
          href="/register"
          className="text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          {t("createAccount")}
        </Link>
      </p>
    </>
  );
}
