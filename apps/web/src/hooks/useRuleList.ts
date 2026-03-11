'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  fetchRules,
  deleteRule as deleteRuleApi,
  toggleRuleActive,
} from '@/lib/api/rules';
import { isPlanError } from '@/lib/api-client';
import type { PlanErrorInfo } from '@/components/UpgradeModal';
import type {
  AutomationRuleResponse,
  RuleFilters,
  RuleType,
} from '@/lib/types/rule';

interface UseRuleListReturn {
  rules: AutomationRuleResponse[];
  count: number;
  isLoading: boolean;
  error: string | null;
  planError: PlanErrorInfo | null;
  filters: RuleFilters;
  setRuleType: (ruleType: RuleType | undefined) => void;
  setActiveFilter: (isActive: boolean | undefined) => void;
  refresh: () => void;
  removeRule: (id: string) => Promise<void>;
  toggleActive: (id: string, isActive: boolean) => Promise<void>;
}

/**
 * Manages automation rule list state including filters and CRUD operations.
 */
export function useRuleList(): UseRuleListReturn {
  const [rules, setRules] = useState<AutomationRuleResponse[]>([]);
  const [count, setCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<PlanErrorInfo | null>(null);
  const [filters, setFilters] = useState<RuleFilters>({});

  const load = useCallback(async (f: RuleFilters) => {
    setIsLoading(true);
    setError(null);
    setPlanError(null);
    try {
      const result = await fetchRules(f);
      setRules(result.items);
      setCount(result.count);
    } catch (err) {
      if (isPlanError(err)) {
        setPlanError(err.planError as PlanErrorInfo);
      } else {
        setError('Greška pri učitavanju pravila');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filters);
  }, [filters, load]);

  const setRuleType = useCallback((ruleType: RuleType | undefined) => {
    setFilters((prev) => ({ ...prev, rule_type: ruleType }));
  }, []);

  const setActiveFilter = useCallback((isActive: boolean | undefined) => {
    setFilters((prev) => ({ ...prev, is_active: isActive }));
  }, []);

  const refresh = useCallback(() => {
    load(filters);
  }, [filters, load]);

  const removeRule = useCallback(
    async (id: string) => {
      try {
        await deleteRuleApi(id);
        load(filters);
      } catch (err) {
        if (isPlanError(err)) setPlanError(err.planError as PlanErrorInfo);
        else setError('Greška pri brisanju pravila');
      }
    },
    [filters, load],
  );

  const toggleActive = useCallback(
    async (id: string, isActive: boolean) => {
      try {
        const updated = await toggleRuleActive(id, isActive);
        setRules((prev) =>
          prev.map((r) => (r.id === id ? updated : r)),
        );
      } catch (err) {
        if (isPlanError(err)) setPlanError(err.planError as PlanErrorInfo);
        else setError('Greška pri ažuriranju pravila');
      }
    },
    [],
  );

  return {
    rules,
    count,
    isLoading,
    error,
    planError,
    filters,
    setRuleType,
    setActiveFilter,
    refresh,
    removeRule,
    toggleActive,
  };
}
