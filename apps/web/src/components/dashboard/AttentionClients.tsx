'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { ClientAvatar } from '@/components/clients/ClientAvatar';
import { fetchPortfolio, type PortfolioRow } from '@/lib/api/portfolio';
import { useOrgPath } from '@/lib/navigation';

const LIMIT = 6;

function severity(row: PortfolioRow): number {
  return row.blocked_count * 10 + row.pending_review_count;
}

export function AttentionClients() {
  const orgPath = useOrgPath();
  const [rows, setRows] = useState<PortfolioRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchPortfolio()
      .then((resp) => {
        if (!cancelled) setRows(resp.data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Greška');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const attention = useMemo(() => {
    if (!rows) return null;
    return [...rows]
      .filter((r) => r.blocked_count > 0 || r.pending_review_count > 0)
      .sort((a, b) => {
        const sev = severity(b) - severity(a);
        if (sev !== 0) return sev;
        return a.name.localeCompare(b.name, 'sr-Latn');
      });
  }, [rows]);

  if (error) {
    // Non-blocking — the dashboard still renders; just hide the section.
    return null;
  }

  if (rows === null) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 animate-pulse">
        <div className="h-5 w-48 bg-gray-100 rounded mb-4" />
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 bg-gray-50 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const attentionList = attention ?? [];
  const topAttention = attentionList.slice(0, LIMIT);
  const hasMore = attentionList.length > LIMIT;

  return (
    <section className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-gray-900">Klijenti koji zahtevaju pažnju</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {attentionList.length > 0
              ? `${attentionList.length} od ${rows.length} klijenata ima fakture na pregledu ili blokirane.`
              : 'Trenutno nema klijenata kojima je potrebna pažnja.'}
          </p>
        </div>
        {attentionList.length > 0 && (
          <span className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 ring-1 ring-amber-600/20">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            {attentionList.length}
          </span>
        )}
      </div>

      {attentionList.length === 0 ? (
        <div className="px-6 py-10 text-center">
          <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-emerald-900">Sve je u redu</p>
          <p className="text-xs text-emerald-700/80 mt-1">
            Nijedan klijent trenutno nema fakture koje čekaju pregled ili su blokirane.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-gray-100">
          {topAttention.map((row) => (
            <li key={row.client_id}>
              <Link
                href={orgPath(`/klijenti/${row.client_id}`)}
                className="flex items-center gap-3 px-6 py-3 hover:bg-amber-50/30 transition-colors"
              >
                <ClientAvatar name={row.name} seed={row.client_id} size="md" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900 truncate">{row.name}</p>
                  <p className="text-[11px] text-gray-500 tabular-nums">PIB {row.pib}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {row.blocked_count > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium text-rose-700 bg-rose-50 ring-1 ring-inset ring-rose-200">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                      {row.blocked_count} blokirano
                    </span>
                  )}
                  {row.pending_review_count > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium text-amber-700 bg-amber-50 ring-1 ring-inset ring-amber-200">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      {row.pending_review_count} na pregledu
                    </span>
                  )}
                </div>
                <svg className="w-4 h-4 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {hasMore && (
        <div className="px-6 py-3 border-t border-gray-100 bg-gray-50/50">
          <Link
            href={orgPath('/klijenti')}
            className="text-sm font-medium text-violet-600 hover:text-violet-700 inline-flex items-center gap-1.5 transition-colors group"
          >
            Pogledaj sve klijente
            <svg className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
        </div>
      )}
    </section>
  );
}
