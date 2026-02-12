"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import type { ApiError } from "@/lib/api-client";

function getErrorMessage(error: unknown): string {
  const apiError = error as ApiError;
  if (apiError?.status === 401) return "Pogrešna e-mail adresa ili lozinka";
  if (apiError?.status === 422) return "Molimo unesite ispravne podatke";
  return "Greška u komunikaciji sa serverom. Pokušajte ponovo.";
}

function RegistrationBanner() {
  const searchParams = useSearchParams();
  if (searchParams.get("registered") !== "true") return null;
  return (
    <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl">
      <p className="text-sm text-green-700">
        Registracija uspešna! Prijavite se sa vašim novim nalogom.
      </p>
    </div>
  );
}

export default function LoginPage() {
  const { login } = useAuth();

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
        <h1 className="text-2xl font-bold text-gray-900">Prijavite se</h1>
        <p className="text-sm text-gray-500 mt-2">
          Unesite vaše podatke za pristup nalogu
        </p>
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
            E-mail adresa
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="vas@email.com"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="email"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            Lozinka
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Unesite lozinku"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="current-password"
          />
          <div className="flex justify-end mt-1.5">
            <Link
              href="/password-reset"
              className="text-sm text-violet-600 hover:text-violet-700 transition-colors"
            >
              Zaboravili ste lozinku?
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
          {isLoading ? "Prijava u toku..." : "Prijavite se"}
        </button>
      </form>

      <p className="text-center text-sm text-gray-500 mt-6">
        Nemate nalog?{" "}
        <Link
          href="/register"
          className="text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          Registrujte se
        </Link>
      </p>
    </>
  );
}
