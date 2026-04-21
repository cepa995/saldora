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
      <div className="flex items-center justify-between gap-3">
        <div>
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
          Dodaj pravilo
        </button>
      </div>

      {/* Attach picker — inline, not a modal */}
      {pickerOpen && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/30 p-4 space-y-2">
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
              {attachable.map((rule) => (
                <li key={rule.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-stone-900 truncate">
                        {rule.name}
                      </span>
                      <span className="text-[11px] text-stone-500 uppercase tracking-wider">
                        {ruleTypeLabel(rule.rule_type)}
                      </span>
                      {rule.client_ids.length === 0 && (
                        <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                          Svi klijenti
                        </span>
                      )}
                    </div>
                    {rule.description && (
                      <p className="text-xs text-stone-500 mt-0.5 truncate">{rule.description}</p>
                    )}
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
              ))}
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
        <ul className="divide-y divide-stone-100 rounded-2xl border border-stone-200 bg-white overflow-hidden">
          {attachedList.map((rule) => (
            <li
              key={rule.id}
              className="p-4 flex items-start justify-between gap-3 hover:bg-stone-50/60 transition-colors"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-stone-900">{rule.name}</span>
                  <span className="text-[11px] text-stone-500 uppercase tracking-wider">
                    {ruleTypeLabel(rule.rule_type)}
                  </span>
                  {!rule.is_active && (
                    <span className="text-[11px] font-medium text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded">
                      Neaktivno
                    </span>
                  )}
                </div>
                {rule.description && (
                  <p className="text-xs text-stone-500 mt-1">{rule.description}</p>
                )}
                <div className="text-[11px] text-stone-400 tabular-nums mt-1.5 flex items-center gap-3">
                  <span>Prioritet {rule.priority}</span>
                  <span>· {rule.execution_count} primena</span>
                  {rule.client_ids.length > 1 && (
                    <span>· primenjuje se i na {rule.client_ids.length - 1} drugih klijenata</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <Link
                  href={orgPath(`/rules?rule=${rule.id}`)}
                  className="text-xs font-medium text-stone-600 hover:text-stone-900 px-2.5 py-1.5 hover:bg-stone-100 rounded-md transition-colors"
                >
                  Izmeni
                </Link>
                <button
                  type="button"
                  onClick={() => handleDetach(rule.id)}
                  disabled={mutatingId === rule.id}
                  className="text-xs font-medium text-rose-600 hover:text-rose-800 px-2.5 py-1.5 hover:bg-rose-50 rounded-md transition-colors disabled:opacity-50"
                >
                  Skini
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Global rules — read-only context */}
      {globalRules.length > 0 && (
        <div>
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-stone-500 mb-2">
            Globalna pravila — primenjuju se na sve klijente
          </h3>
          <ul className="divide-y divide-stone-100 rounded-2xl border border-stone-200 bg-stone-50/40">
            {globalRules.map((rule) => (
              <li key={rule.id} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-stone-800">{rule.name}</span>
                    <span className="text-[11px] text-stone-500 uppercase tracking-wider">
                      {ruleTypeLabel(rule.rule_type)}
                    </span>
                    {!rule.is_active && (
                      <span className="text-[11px] font-medium text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded">
                        Neaktivno
                      </span>
                    )}
                  </div>
                </div>
                <Link
                  href={orgPath(`/rules?rule=${rule.id}`)}
                  className="text-xs font-medium text-stone-500 hover:text-stone-800 shrink-0"
                >
                  Otvori →
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
