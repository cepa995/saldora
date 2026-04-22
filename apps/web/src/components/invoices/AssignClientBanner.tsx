'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import type { ClientResponse } from '@/lib/types/client';

interface Props {
  /** All clients in the org — used to populate the picker and find PIB matches. */
  clients: ClientResponse[];
  /** PIB values we know from the invoice (seller + buyer). Either can match. */
  knownPibs: (string | null | undefined)[];
  /** Fired when the user confirms a client assignment. */
  onAssign: (clientId: string) => void | Promise<void>;
  /** Disables buttons during the assignment network call. */
  isAssigning: boolean;
}

/**
 * Unassigned-invoice banner with an inline picker. Surfaces a PIB-matched
 * suggestion when possible so the common case is a single click.
 */
export function AssignClientBanner({ clients, knownPibs, onAssign, isAssigning }: Props) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  // PIB-matched suggestion. Takes the first match among seller/buyer PIBs.
  const suggested = useMemo(() => {
    const pibs = knownPibs.filter((p): p is string => Boolean(p));
    if (pibs.length === 0) return null;
    return clients.find((c) => pibs.includes(c.pib)) ?? null;
  }, [clients, knownPibs]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return clients;
    return clients.filter(
      (c) => c.name.toLowerCase().includes(q) || c.pib.includes(q),
    );
  }, [clients, search]);

  // Close picker on outside click
  useEffect(() => {
    if (!pickerOpen) return;
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [pickerOpen]);

  return (
    <div
      ref={containerRef}
      className="relative rounded-xl border border-amber-200 bg-amber-50/50 px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3"
    >
      <div className="flex items-start gap-3 min-w-0 flex-1">
        <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M4.93 19h14.14c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.2 16c-.77 1.33.19 3 1.73 3z" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-amber-900">
            Ova faktura nije dodeljena klijentu
          </p>
          <p className="text-xs text-amber-700 mt-0.5">
            {suggested
              ? `Prepoznati PIB odgovara klijentu ${suggested.name}.`
              : 'Dodelite klijenta da se faktura pojavi u njegovom radnom prostoru.'}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        {suggested && (
          <button
            type="button"
            onClick={() => onAssign(suggested.id)}
            disabled={isAssigning}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 text-white text-sm font-medium hover:bg-amber-700 transition-colors disabled:opacity-50"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.25} d="M5 13l4 4L19 7" />
            </svg>
            Dodeli — {suggested.name}
          </button>
        )}
        <button
          type="button"
          onClick={() => setPickerOpen((p) => !p)}
          disabled={isAssigning}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white ring-1 ring-amber-300 text-amber-800 text-sm font-medium hover:bg-amber-100 transition-colors disabled:opacity-50"
        >
          {suggested ? 'Dodeli drugom' : 'Dodeli klijentu'}
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {pickerOpen && (
        <div className="absolute top-full right-2 mt-1 z-30 w-full sm:w-80 max-h-80 overflow-hidden bg-white rounded-xl shadow-xl ring-1 ring-gray-200 flex flex-col">
          <div className="p-2 border-b border-gray-100">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Pretraži po nazivu ili PIB-u"
              className="w-full px-3 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            />
          </div>
          <ul className="overflow-y-auto flex-1">
            {filtered.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-gray-500">
                Nema rezultata
              </li>
            ) : (
              filtered.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onAssign(c.id);
                      setPickerOpen(false);
                    }}
                    disabled={isAssigning}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 transition-colors flex items-baseline justify-between gap-2"
                  >
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {c.name}
                    </span>
                    <span className="text-xs text-gray-400 tabular-nums shrink-0">
                      {c.pib}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
