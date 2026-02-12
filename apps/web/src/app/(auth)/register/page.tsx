"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import type { ApiError } from "@/lib/api-client";

function getErrorMessage(error: unknown): string {
  const apiError = error as ApiError;
  if (apiError?.status === 409)
    return "Korisnik sa ovom e-mail adresom već postoji";
  if (apiError?.status === 422) return "Molimo unesite ispravne podatke";
  return "Greška u komunikaciji sa serverom. Pokušajte ponovo.";
}

export default function RegisterPage() {
  const { register } = useAuth();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Lozinka mora imati minimum 8 karaktera");
      return;
    }
    if (password !== confirmPassword) {
      setError("Lozinke se ne poklapaju");
      return;
    }

    setIsLoading(true);
    try {
      await register({
        email,
        password,
        firstName: firstName || undefined,
        lastName: lastName || undefined,
        organizationName: organizationName || undefined,
      });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Registrujte se</h1>
        <p className="text-sm text-gray-500 mt-2">
          Kreirajte nalog i počnite sa obradom faktura
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="firstName"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              Ime
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
              Prezime
            </label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Petrović"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
              autoComplete="family-name"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            E-mail adresa <span className="text-red-500">*</span>
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
            htmlFor="organizationName"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            Naziv organizacije
          </label>
          <input
            id="organizationName"
            type="text"
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            placeholder="Vaša firma d.o.o."
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="organization"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            Lozinka <span className="text-red-500">*</span>
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Unesite lozinku"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all"
            autoComplete="new-password"
          />
          <p className="text-xs text-gray-500 mt-1">Minimum 8 karaktera</p>
        </div>

        <div>
          <label
            htmlFor="confirmPassword"
            className="block text-sm font-medium text-gray-700 mb-1.5"
          >
            Potvrdite lozinku <span className="text-red-500">*</span>
          </label>
          <input
            id="confirmPassword"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Ponovite lozinku"
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
          disabled={isLoading}
          className="w-full py-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium rounded-xl transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-violet-500/30 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
        >
          {isLoading ? "Registracija u toku..." : "Registrujte se"}
        </button>
      </form>

      <p className="text-center text-sm text-gray-500 mt-6">
        Već imate nalog?{" "}
        <Link
          href="/login"
          className="text-violet-600 font-medium hover:text-violet-700 transition-colors"
        >
          Prijavite se
        </Link>
      </p>
    </>
  );
}
