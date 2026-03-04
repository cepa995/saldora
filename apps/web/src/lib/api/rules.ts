/**
 * Automation rules API service functions.
 *
 * Typed wrappers around the apiClient for rules-related endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type {
  AutomationRuleCreate,
  AutomationRuleListResponse,
  AutomationRuleResponse,
  AutomationRuleUpdate,
  RuleExecutionResponse,
  RuleFilters,
  RuleTemplate,
} from '@/lib/types/rule';

/**
 * Fetch automation rules for the current organization.
 *
 * Args:
 *   filters - Optional filters for rule_type and is_active.
 * Returns:
 *   List of rules with count.
 */
export async function fetchRules(
  filters: Partial<RuleFilters> = {},
): Promise<AutomationRuleListResponse> {
  const params = new URLSearchParams();

  if (filters.rule_type) params.set('rule_type', filters.rule_type);
  if (filters.is_active !== undefined)
    params.set('is_active', String(filters.is_active));

  const query = params.toString();
  const endpoint = query ? `/api/v1/rules?${query}` : '/api/v1/rules';

  return apiClient<AutomationRuleListResponse>(endpoint);
}

/**
 * Fetch a single automation rule by ID.
 *
 * Args:
 *   id - UUID of the rule.
 * Returns:
 *   Full rule response.
 */
export async function fetchRule(id: string): Promise<AutomationRuleResponse> {
  return apiClient<AutomationRuleResponse>(`/api/v1/rules/${id}`);
}

/**
 * Create a new automation rule.
 *
 * Args:
 *   data - Rule creation payload.
 * Returns:
 *   Created rule response.
 */
export async function createRule(
  data: AutomationRuleCreate,
): Promise<AutomationRuleResponse> {
  return apiClient<AutomationRuleResponse>('/api/v1/rules', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing automation rule.
 *
 * Args:
 *   id - UUID of the rule.
 *   data - Partial update payload.
 * Returns:
 *   Updated rule response.
 */
export async function updateRule(
  id: string,
  data: AutomationRuleUpdate,
): Promise<AutomationRuleResponse> {
  return apiClient<AutomationRuleResponse>(`/api/v1/rules/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete an automation rule.
 *
 * Args:
 *   id - UUID of the rule to delete.
 */
export async function deleteRule(id: string): Promise<void> {
  await apiClient<void>(`/api/v1/rules/${id}`, { method: 'DELETE' });
}

/**
 * Fetch pre-built rule templates.
 *
 * Returns:
 *   List of rule templates for common Serbian accounting scenarios.
 */
export async function fetchRuleTemplates(): Promise<RuleTemplate[]> {
  return apiClient<RuleTemplate[]>('/api/v1/rules/templates');
}

/**
 * Fetch execution history for a rule.
 *
 * Args:
 *   ruleId - UUID of the rule.
 *   limit - Max number of executions to return.
 * Returns:
 *   List of rule execution entries.
 */
export async function fetchRuleExecutions(
  ruleId: string,
  limit: number = 50,
): Promise<RuleExecutionResponse[]> {
  return apiClient<RuleExecutionResponse[]>(
    `/api/v1/rules/${ruleId}/executions?limit=${limit}`,
  );
}

/**
 * Toggle a rule's active status.
 *
 * Args:
 *   id - UUID of the rule.
 *   isActive - New active state.
 * Returns:
 *   Updated rule response.
 */
export async function toggleRuleActive(
  id: string,
  isActive: boolean,
): Promise<AutomationRuleResponse> {
  return apiClient<AutomationRuleResponse>(`/api/v1/rules/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}
