/**
 * TypeScript interfaces mirroring backend automation rule schemas.
 *
 * These types are shared across the rules management page.
 */

export type RuleType =
  | 'KONTO_ASSIGNMENT'
  | 'VAT_TREATMENT'
  | 'AUTO_APPROVE'
  | 'FLAG_FOR_REVIEW'
  | 'DOCUMENT_TYPE'
  | 'CUSTOM_FIELD';

export type ConditionOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'starts_with'
  | 'ends_with'
  | 'regex'
  | 'greater_than'
  | 'less_than'
  | 'between'
  | 'in'
  | 'not_in'
  | 'is_null'
  | 'is_not_null';

export type ActionType =
  | 'SET_KONTO'
  | 'SET_VAT_TREATMENT'
  | 'FLAG_REVIEW'
  | 'AUTO_APPROVE'
  | 'SET_CUSTOM_FIELD';

export interface ConditionRule {
  field: string;
  operator: ConditionOperator;
  value: unknown;
}

export interface ConditionGroup {
  operator: 'AND' | 'OR';
  rules: (ConditionRule | ConditionGroup)[];
}

export interface RuleAction {
  type: ActionType;
  target?: string;
  value?: unknown;
  description?: string;
  reason?: string;
}

export interface AutomationRuleCreate {
  name: string;
  description?: string;
  rule_type: RuleType;
  priority?: number;
  conditions: ConditionGroup;
  actions: RuleAction[];
  is_active?: boolean;
}

export interface AutomationRuleUpdate {
  name?: string;
  description?: string;
  rule_type?: RuleType;
  priority?: number;
  conditions?: ConditionGroup;
  actions?: RuleAction[];
  is_active?: boolean;
}

export interface AutomationRuleResponse {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  rule_type: RuleType;
  priority: number;
  conditions: ConditionGroup;
  actions: RuleAction[];
  is_active: boolean;
  created_by: string;
  updated_by: string | null;
  execution_count: number;
  last_executed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRuleListResponse {
  items: AutomationRuleResponse[];
  count: number;
}

export interface RuleExecutionResponse {
  id: string;
  rule_id: string;
  invoice_id: string;
  accounting_intent_id: string | null;
  conditions_matched: Record<string, unknown>;
  actions_applied: RuleAction[];
  executed_at: string;
  execution_time_ms: number | null;
}

export interface RuleTemplate {
  name: string;
  description: string;
  rule_type: RuleType;
  conditions: ConditionGroup;
  actions: RuleAction[];
  priority: number;
}

export interface RuleFilters {
  rule_type?: RuleType;
  is_active?: boolean;
}
