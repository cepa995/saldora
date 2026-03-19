'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchPrivacyPolicy, type PrivacyPolicy } from '@/lib/api/compliance';

export default function PrivacyPolicyPage() {
  const [policy, setPolicy] = useState<PrivacyPolicy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPrivacyPolicy()
      .then(setPolicy)
      .catch(() => setError('Greška pri učitavanju politike privatnosti'));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="text-sm text-violet-600 hover:text-violet-700 font-medium transition-colors"
          >
            &larr; Nazad na početnu
          </Link>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Politika privatnosti
          </h1>

          {policy && (
            <p className="text-sm text-gray-500 mb-6">
              Verzija {policy.version} — važi od{' '}
              {new Date(policy.effective_date).toLocaleDateString('sr-Latn-RS', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </p>
          )}

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl mb-6">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {!policy && !error && (
            <div className="space-y-3">
              {[85, 92, 78, 95, 70].map((w, i) => (
                <div
                  key={i}
                  className="h-4 bg-gray-100 rounded animate-pulse"
                  style={{ width: `${w}%` }}
                />
              ))}
            </div>
          )}

          {policy && (
            <div className="prose prose-sm prose-gray max-w-none">
              {policy.content.split('\n').map((line, i) => {
                if (!line.trim()) return <br key={i} />;
                if (/^\d+\./.test(line.trim())) {
                  return (
                    <h2
                      key={i}
                      className="text-base font-semibold text-gray-900 mt-6 mb-2"
                    >
                      {line.trim()}
                    </h2>
                  );
                }
                if (line.trim().startsWith('-')) {
                  return (
                    <p key={i} className="text-sm text-gray-600 ml-4">
                      {line.trim()}
                    </p>
                  );
                }
                return (
                  <p key={i} className="text-sm text-gray-600">
                    {line.trim()}
                  </p>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
