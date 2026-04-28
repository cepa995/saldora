'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  attachRuleToClient,
  detachRuleFromClient,
  fetchClientRules,
  fetchRules,
} from '@/lib/api/rules';
import { useOrgPath } from '@/lib/navigation';
import type { AutomationRuleResponse } from '@/lib/types/rule';

interface Props {
  clientId: string;
}

function ruleTypeLabel(ruleType: string): string {
  const map: Record<string, string> = {
    KONTO_ASSIGNMENT: 'Dodela konta',
    VAT_TREATMENT: 'PDV tretman',
    AUTO_APPROVE: 'Auto-odobri',
    FLAG_FOR_REVIEW: 'Za pregled',
    DOCUMENT_TYPE: 'Tip dokumenta',
    CUSTOM_FIELD: 'Prilagođeno',
  };
  return map[ruleType] ?? ruleType;
}

const TYPE_CHIP: Record<string, string> = {
  KONTO_ASSIGNMENT: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  VAT_TREATMENT: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  AUTO_APPROVE: 'bg-green-50 text-green-700 ring-green-600/20',
  FLAG_FOR_REVIEW: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  DOCUMENT_TYPE: 'bg-purple-50 text-purple-700 ring-purple-600/20',
  CUSTOM_FIELD: 'bg-stone-100 text-stone-700 ring-stone-600/20',
};

const TYPE_ACCENT: Record<string, string> = {
  KONTO_ASSIGNMENT: 'bg-blue-400',
  VAT_TREATMENT: 'bg-emerald-400',
  AUTO_APPROVE: 'bg-green-400',
  FLAG_FOR_REVIEW: 'bg-amber-400',
  DOCUMENT_TYPE: 'bg-purple-400',
  CUSTOM_FIELD: 'bg-stone-400',
};

function lastExecutedLabel(iso: string | null): string {
  if (!iso) return 'Nije još primenjeno';
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'Pre manje od minuta';
  if (minutes < 60) return `Pre ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Pre ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `Pre ${days} d`;
  return new Date(iso).toLocaleDateString('sr-Latn', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function ClientRules({ clientId }: Props) {
  const tCommon = useTranslations('common');
  const orgPath = useOrgPath();

  const [attached, setAttached] = useState<AutomationRuleResponse[] | null>(null);
  const [library, setLibrary] = useState<AutomationRuleResponse[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutatingId, setMutatingId] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [a, l] = await Promise.all([
        fetchClientRules(clientId),
        fetchRules(),
      ]);
      setAttached(a);
      setLibrary(l.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setIsLoading(false);
    }
  }, [clientId, tCommon]);

  useEffect(() => {
    void load();
  }, [load]);

  const attachedIds = useMemo(
    () => new Set((attached ?? []).map((r) => r.id)),
    [attached],
  );

  // Rules in the library that aren't yet attached to this client.
  // Global rules (client_ids empty) remain in the picker — attaching narrows them.
  const attachable = useMemo(
    () => (library ?? []).filter((r) => !attachedIds.has(r.id)),
    [library, attachedIds],
  );

  // Global rules in the library — shown as context below the attached list.
  const globalRules = useMemo(
    () => (library ?? []).filter((r) => r.client_ids.length === 0),
    [library],
  );

  async function handleAttach(ruleId: string) {
    setMutatingId(ruleId);
    try {
      await attachRuleToClient(clientId, ruleId);
      await load();
      setPickerOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setMutatingId(null);
    }
  }

  async function handleDetach(ruleId: string) {
    setMutatingId(ruleId);
    try {
      await detachRuleFromClient(clientId, ruleId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon('error'));
    } finally {
      setMutatingId(null);
    }
  }

  if (error) {
    return (
      <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm">
        {error}
      </div>
    );
  }

  if (isLoading && attached === null) {
    return (
      <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-500">
        {tCommon('loading')}
      </div>
    );
  }

  const attachedList = attached ?? [];

  return (
    <div className="space-y-6">
      {/* Header — "Attach rule" action */}
      <div className="flex items-start sm:items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-stone-900">Pravila za ovog klijenta</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Pravila koja se primenjuju samo na fakture ovog klijenta. Dodajte postojeće pravilo iz biblioteke.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setPickerOpen((p) => !p)}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors shrink-0 shadow-sm shadow-violet-600/10"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.25} d="M12 4v16m8-8H4" />
          </svg>
          <span className="hidden sm:inline">Dodaj pravilo</span>
          <span className="sm:hidden">Dodaj</span>
        </button>
      </div>

      {/* Attach picker — inline, not a modal. Cap at ~half the viewport
          on mobile so a long library doesn't push attached rules below
          the fold. */}
      {pickerOpen && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/30 p-4 space-y-2 max-h-[60vh] overflow-y-auto">
          <div className="flex items-center justify-between gap-3 mb-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-900">
              Izaberi pravilo iz biblioteke
            </h3>
            <button
              type="button"
              onClick={() => setPickerOpen(false)}
              className="text-xs text-stone-500 hover:text-stone-700"
            >
              {tCommon('cancel')}
            </button>
          </div>
          {attachable.length === 0 ? (
            <p className="text-sm text-stone-500 py-4 text-center">
              Sva pravila su već dodata ovom klijentu, ili biblioteka je prazna.{' '}
              <Link href={orgPath('/rules')} className="text-violet-700 hover:underline">
                Otvori biblioteku →
              </Link>
            </p>
          ) : (
            <ul className="divide-y divide-violet-100">
              {attachable.map((rule) => {
                const chip =
                  TYPE_CHIP[rule.rule_type] ?? 'bg-stone-100 text-stone-700 ring-stone-600/20';
                return (
                  <li key={rule.id} className="py-2.5 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1 flex items-center gap-2.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ring-1 ring-inset shrink-0 ${chip}`}
                      >
                        {ruleTypeLabel(rule.rule_type)}
                      </span>
                      <div className="min-w-0">
                        <span className="text-sm font-medium text-stone-900 truncate block">
                          {rule.name}
                        </span>
                        {rule.description && (
                          <p className="text-[11px] text-stone-500 truncate">{rule.description}</p>
                        )}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleAttach(rule.id)}
                      disabled={mutatingId === rule.id}
                      className="px-3 py-1.5 text-xs font-medium text-violet-700 bg-white hover:bg-violet-50 ring-1 ring-violet-200 rounded-lg transition-colors disabled:opacity-50 shrink-0"
                    >
                      Dodaj
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* Attached rules list */}
      {attachedList.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-200 bg-white/60 p-10 text-center">
          <p className="text-sm text-stone-500">
            Ovom klijentu nije dodato nijedno pravilo. Globalna pravila se i dalje primenjuju.
          </p>
        </div>
      ) : (
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {attachedList.map((rule) => {
            const accent = TYPE_ACCENT[rule.rule_type] ?? 'bg-stone-400';
            const chip = TYPE_CHIP[rule.rule_type] ?? 'bg-stone-100 text-stone-700 ring-stone-600/20';
            return (
              <li
                key={rule.id}
                className={`group relative rounded-2xl bg-white ring-1 ring-stone-200 hover:ring-stone-300 hover:shadow-sm shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-all overflow-hidden ${
                  !rule.is_active ? 'opacity-60' : ''
                }`}
              >
                {/* Left accent stripe — colored by rule type */}
                <span
                  className={`absolute left-0 top-0 bottom-0 w-[3px] ${accent}`}
                  aria-hidden="true"
                />

                <div className="p-4 pl-5 flex flex-col gap-2.5">
                  {/* Header: name + type chip */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-[15px] font-semibold text-stone-900 leading-snug truncate">
                        {rule.name}
                      </h3>
                      <div className="flex items-center gap-1.5 flex-wrap mt-1.5">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ring-1 ring-inset ${chip}`}
                        >
                          {ruleTypeLabel(rule.rule_type)}
                        </span>
                        {!rule.is_active && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-stone-100 text-stone-600 ring-1 ring-inset ring-stone-300">
                            Neaktivno
                          </span>
                        )}
                        {rule.client_ids.length > 1 && (
                          <span
                            className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-600/20"
                            title={`Deli se sa još ${rule.client_ids.length - 1} klijenata`}
                          >
                            +{rule.client_ids.length - 1}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  {rule.description && (
                    <p className="text-[13px] text-stone-600 leading-relaxed line-clamp-2">
                      {rule.description}
                    </p>
                  )}

                  {/* Footer: meta stats + actions */}
                  <div className="flex items-center justify-between gap-3 pt-1 border-t border-stone-100 mt-1">
                    <div className="text-[11px] text-stone-500 tabular-nums flex items-center gap-3 min-w-0">
                      <span className="inline-flex items-center gap-1">
                        <svg className="w-3 h-3 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        {rule.execution_count}
                      </span>
                      <span className="truncate">{lastExecutedLabel(rule.last_executed_at)}</span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Link
                        href={orgPath(`/rules?rule=${rule.id}`)}
                        className="px-2.5 py-1 text-[12px] font-medium text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-md transition-colors"
                      >
                        Izmeni
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleDetach(rule.id)}
                        disabled={mutatingId === rule.id}
                        className="px-2.5 py-1 text-[12px] font-medium text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-md transition-colors disabled:opacity-50"
                      >
                        Skini
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Global rules — read-only context */}
      {globalRules.length > 0 && (
        <div>
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-stone-500">
              Globalna pravila
            </h3>
            <span className="text-[11px] text-stone-400">primenjuju se na sve klijente</span>
          </div>
          <ul className="divide-y divide-stone-200/60 rounded-2xl border border-stone-200 bg-stone-50/40 overflow-hidden">
            {globalRules.map((rule) => {
              const chip =
                TYPE_CHIP[rule.rule_type] ?? 'bg-stone-100 text-stone-700 ring-stone-600/20';
              return (
                <li
                  key={rule.id}
                  className="px-4 py-3 flex items-center justify-between gap-3 hover:bg-white/60 transition-colors"
                >
                  <div className="min-w-0 flex-1 flex items-center gap-2.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ring-1 ring-inset shrink-0 ${chip}`}
                    >
                      {ruleTypeLabel(rule.rule_type)}
                    </span>
                    <span className="text-sm text-stone-800 truncate">{rule.name}</span>
                    {!rule.is_active && (
                      <span className="text-[11px] font-medium text-stone-500 bg-white ring-1 ring-stone-300 px-1.5 py-0.5 rounded shrink-0">
                        Neaktivno
                      </span>
                    )}
                  </div>
                  <Link
                    href={orgPath(`/rules?rule=${rule.id}`)}
                    className="text-xs font-medium text-stone-500 hover:text-stone-800 shrink-0"
                  >
                    Otvori →
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
