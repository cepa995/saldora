'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchPrivacyPolicy, type PrivacyPolicy } from '@/lib/api/compliance';

export default function PrivacyPolicyPage() {
  const [policy, setPolicy] = useState<PrivacyPolicy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    fetchPrivacyPolicy()
      .then(setPolicy)
      .catch(() => setError('Greška pri učitavanju politike privatnosti'));
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-violet-50/50 to-white">
      {/* Navigation — matches landing page style */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled
            ? 'bg-white/90 backdrop-blur-xl shadow-lg shadow-violet-500/5 py-3'
            : 'bg-transparent py-5'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center">
              <span className="text-xl font-bold bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">
                FakturaAI
              </span>
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="px-5 py-2.5 text-sm font-medium text-gray-700 hover:text-violet-600 transition-colors"
              >
                Prijavite se
              </Link>
              <Link
                href="/register"
                className="px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:shadow-lg hover:shadow-violet-500/25 transition-all"
              >
                Započnite besplatno
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero section */}
      <div className="pt-32 pb-12 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-violet-100 text-violet-700 rounded-full text-sm font-medium mb-6">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            ZZPL usklađenost
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Politika privatnosti
          </h1>
          {policy && (
            <p className="text-lg text-gray-500">
              Verzija {policy.version} — važi od{' '}
              {new Date(policy.effective_date).toLocaleDateString('sr-Latn-RS', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </p>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 pb-24">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-2xl mb-6">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {!policy && !error && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 space-y-4">
            {[85, 92, 78, 95, 70, 88, 75, 90].map((w, i) => (
              <div
                key={i}
                className="h-4 bg-gray-100 rounded animate-pulse"
                style={{ width: `${w}%` }}
              />
            ))}
          </div>
        )}

        {policy && (
          <div className="space-y-6">
            {policy.content.split(/\n(?=\d+\.)/).map((section, i) => {
              const lines = section.trim().split('\n');
              const heading = lines[0];
              const body = lines.slice(1);

              if (!heading) return null;

              return (
                <div
                  key={i}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 hover:shadow-md transition-shadow"
                >
                  <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-violet-500 rounded-full shrink-0" />
                    {heading.trim()}
                  </h2>
                  <div className="space-y-1.5 pl-3.5">
                    {body.map((line, j) => {
                      const trimmed = line.trim();
                      if (!trimmed) return null;
                      if (trimmed.startsWith('-')) {
                        return (
                          <p
                            key={j}
                            className="text-sm text-gray-600 flex items-start gap-2"
                          >
                            <span className="text-violet-400 mt-0.5">
                              &bull;
                            </span>
                            {trimmed.slice(1).trim()}
                          </p>
                        );
                      }
                      if (trimmed.startsWith('http')) {
                        return (
                          <a
                            key={j}
                            href={trimmed}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-violet-600 hover:text-violet-700 underline block"
                          >
                            {trimmed}
                          </a>
                        );
                      }
                      return (
                        <p key={j} className="text-sm text-gray-600">
                          {trimmed}
                        </p>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Back link */}
        <div className="mt-12 text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-violet-600 hover:text-violet-700 font-medium transition-colors"
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
                strokeWidth={2}
                d="M7 16l-4-4m0 0l4-4m-4 4h18"
              />
            </svg>
            Nazad na početnu stranicu
          </Link>
        </div>
      </div>
    </div>
  );
}
