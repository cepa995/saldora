'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { useOrgPath } from '@/lib/navigation';
import { AccessDenied } from '@/components';
import { useRuleList } from '@/hooks/useRuleList';
import {
  createRule,
  updateRule,
  fetchRuleTemplates,
  fetchRuleExecutions,
} from '@/lib/api/rules';
import { formatRelativeTime, formatDateSr } from '@/lib/formatters';
import type {
  RuleType,
  ActionType,
  ConditionOperator,
  ConditionRule,
  ConditionGroup,
  RuleAction,
  AutomationRuleResponse,
  AutomationRuleCreate,
  AutomationRuleUpdate,
  RuleTemplate,
  RuleExecutionResponse,
} from '@/lib/types/rule';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type TranslationFn = ReturnType<typeof useTranslations<any>>;

// ── Constants ──────────────────────────────────────────────────────────────────

const RULE_TYPES: (RuleType | undefined)[] = [
  undefined,
  'KONTO_ASSIGNMENT',
  'VAT_TREATMENT',
  'AUTO_APPROVE',
  'FLAG_FOR_REVIEW',
  'DOCUMENT_TYPE',
  'CUSTOM_FIELD',
];

const RULE_TYPE_COLORS: Record<RuleType, string> = {
  KONTO_ASSIGNMENT: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  VAT_TREATMENT: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  AUTO_APPROVE: 'bg-green-50 text-green-700 ring-green-600/20',
  FLAG_FOR_REVIEW: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  DOCUMENT_TYPE: 'bg-purple-50 text-purple-700 ring-purple-600/20',
  CUSTOM_FIELD: 'bg-gray-50 text-gray-700 ring-gray-600/20',
};

interface FieldOption {
  value: string;
  labelKey: string;
  type: 'text' | 'numeric' | 'boolean' | 'array_text';
}

const FIELD_GROUPS: { labelKey: string; fields: FieldOption[] }[] = [
  {
    labelKey: 'fieldGroup_seller',
    fields: [
      { value: 'seller.pib', labelKey: 'PIB', type: 'text' },
      { value: 'seller.name', labelKey: 'Naziv', type: 'text' },
      { value: 'seller.address', labelKey: 'Adresa', type: 'text' },
      { value: 'seller.city', labelKey: 'Grad', type: 'text' },
    ],
  },
  {
    labelKey: 'fieldGroup_buyer',
    fields: [
      { value: 'buyer.pib', labelKey: 'PIB', type: 'text' },
      { value: 'buyer.name', labelKey: 'Naziv', type: 'text' },
      { value: 'buyer.address', labelKey: 'Adresa', type: 'text' },
      { value: 'buyer.city', labelKey: 'Grad', type: 'text' },
    ],
  },
  {
    labelKey: 'fieldGroup_amounts',
    fields: [
      { value: 'total_amount', labelKey: 'Ukupan iznos', type: 'numeric' },
      { value: 'subtotal', labelKey: 'Osnovica', type: 'numeric' },
      { value: 'tax_rate', labelKey: 'Stopa PDV-a', type: 'numeric' },
      { value: 'tax_amount', labelKey: 'Iznos PDV-a', type: 'numeric' },
    ],
  },
  {
    labelKey: 'fieldGroup_items',
    fields: [
      {
        value: 'line_items[].description',
        labelKey: 'Opis stavke',
        type: 'array_text',
      },
    ],
  },
  {
    labelKey: 'fieldGroup_document',
    fields: [
      { value: 'currency', labelKey: 'Valuta', type: 'text' },
      { value: 'document_type', labelKey: 'Tip dokumenta', type: 'text' },
      { value: 'invoice_number', labelKey: 'Broj fakture', type: 'text' },
    ],
  },
  {
    labelKey: 'fieldGroup_system',
    fields: [
      {
        value: 'is_first_from_supplier',
        labelKey: 'Prvi od dobavljača',
        type: 'boolean',
      },
      {
        value: 'supplier_invoice_count',
        labelKey: 'Broj faktura dobavljača',
        type: 'numeric',
      },
      { value: 'confidence', labelKey: 'Pouzdanost', type: 'numeric' },
    ],
  },
];

function getFieldType(
  fieldValue: string,
): 'text' | 'numeric' | 'boolean' | 'array_text' {
  for (const group of FIELD_GROUPS) {
    for (const f of group.fields) {
      if (f.value === fieldValue) return f.type;
    }
  }
  return 'text';
}

function getOperatorsForType(
  fieldType: 'text' | 'numeric' | 'boolean' | 'array_text',
): ConditionOperator[] {
  switch (fieldType) {
    case 'numeric':
      return [
        'equals',
        'not_equals',
        'greater_than',
        'less_than',
        'between',
        'is_null',
        'is_not_null',
      ];
    case 'boolean':
      return ['equals', 'not_equals'];
    case 'array_text':
      return ['contains', 'starts_with', 'ends_with', 'regex'];
    default:
      return [
        'equals',
        'not_equals',
        'contains',
        'starts_with',
        'ends_with',
        'regex',
        'in',
        'not_in',
        'is_null',
        'is_not_null',
      ];
  }
}

const VAT_TREATMENT_OPTIONS = [
  { value: 'DEDUCTIBLE_FULL', labelKey: 'vat_DEDUCTIBLE_FULL' },
  { value: 'DEDUCTIBLE_PARTIAL', labelKey: 'vat_DEDUCTIBLE_PARTIAL' },
  { value: 'NON_DEDUCTIBLE', labelKey: 'vat_NON_DEDUCTIBLE' },
  { value: 'OUTPUT_STANDARD', labelKey: 'vat_OUTPUT_STANDARD' },
  { value: 'OUTPUT_REDUCED', labelKey: 'vat_OUTPUT_REDUCED' },
  { value: 'OUTPUT_EXEMPT', labelKey: 'vat_OUTPUT_EXEMPT' },
  { value: 'REVERSE_CHARGE_IN', labelKey: 'vat_REVERSE_CHARGE_IN' },
  { value: 'REVERSE_CHARGE_OUT', labelKey: 'vat_REVERSE_CHARGE_OUT' },
];

// ── Helper Functions ───────────────────────────────────────────────────────────

function summarizeConditions(conditions: ConditionGroup, t: TranslationFn): string {
  const { operator, rules } = conditions;
  if (!rules || rules.length === 0) return '—';

  const parts = rules.map((rule) => {
    if ('field' in rule) {
      const cr = rule as ConditionRule;
      const fieldLabel = cr.field;
      const opLabel = t(`op_${cr.operator}`);
      if (cr.operator === 'is_null' || cr.operator === 'is_not_null') {
        return `${fieldLabel} ${opLabel}`;
      }
      if (cr.operator === 'between' && Array.isArray(cr.value)) {
        return `${fieldLabel} ${opLabel} ${cr.value[0]} - ${cr.value[1]}`;
      }
      return `${fieldLabel} ${opLabel} "${cr.value}"`;
    }
    return summarizeConditions(rule as ConditionGroup, t);
  });

  const joiner = operator === 'AND' ? ' I ' : ' ILI ';
  return parts.join(joiner);
}

function summarizeActions(actions: RuleAction[], t: TranslationFn): string {
  if (!actions || actions.length === 0) return '—';
  return actions
    .map((a) => {
      switch (a.type) {
        case 'SET_KONTO':
          return `${t('ruleType_KONTO_ASSIGNMENT')}: ${a.value}${a.description ? ` (${a.description})` : ''}`;
        case 'SET_VAT_TREATMENT':
          return `${t('ruleType_VAT_TREATMENT')}: ${a.value}`;
        case 'FLAG_REVIEW':
          return `${t('ruleType_FLAG_FOR_REVIEW')}${a.reason ? `: ${a.reason}` : ''}`;
        case 'AUTO_APPROVE':
          return t('ruleType_AUTO_APPROVE');
        case 'SET_CUSTOM_FIELD':
          return `${a.target}: ${a.value}`;
        default:
          return a.type;
      }
    })
    .join(', ');
}

// ── Main Page Component ────────────────────────────────────────────────────────

export default function RulesPage() {
  const t = useTranslations('rules');
  const tCommon = useTranslations('common');
  const tDetail = useTranslations('detail');
  const { hasRole } = useAuth();
  const {
    rules,
    count,
    isLoading,
    error,
    filters,
    setRuleType,
    setActiveFilter,
    refresh,
    removeRule,
    toggleActive,
  } = useRuleList();

  // Modal states
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<AutomationRuleResponse | null>(
    null,
  );
  const [showTemplates, setShowTemplates] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] =
    useState<AutomationRuleResponse | null>(null);
  const [showHistory, setShowHistory] =
    useState<AutomationRuleResponse | null>(null);
  const [templateData, setTemplateData] = useState<RuleTemplate | null>(null);

  if (!hasRole('manager')) {
    return <AccessDenied />;
  }

  function handleEdit(rule: AutomationRuleResponse) {
    setEditingRule(rule);
    setTemplateData(null);
    setShowForm(true);
  }

  function handleCreate() {
    setEditingRule(null);
    setTemplateData(null);
    setShowForm(true);
  }

  function handleApplyTemplate(tmpl: RuleTemplate) {
    setShowTemplates(false);
    setEditingRule(null);
    setTemplateData(tmpl);
    setShowForm(true);
  }

  async function handleFormSave(data: AutomationRuleCreate | AutomationRuleUpdate) {
    if (editingRule) {
      await updateRule(editingRule.id, data as AutomationRuleUpdate);
    } else {
      await createRule(data as AutomationRuleCreate);
    }
    setShowForm(false);
    setEditingRule(null);
    setTemplateData(null);
    refresh();
  }

  async function handleDelete() {
    if (!showDeleteConfirm) return;
    await removeRule(showDeleteConfirm.id);
    setShowDeleteConfirm(null);
  }

  // Active filter state: undefined = all, true = active, false = inactive
  const activeFilterValue = filters.is_active;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('subtitle')}</p>
        </div>
        <div className="flex items-center justify-center sm:justify-end gap-3">
          <button
            onClick={() => setShowTemplates(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 text-sm font-medium text-gray-700 rounded-xl hover:bg-gray-50 transition-all"
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
                d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
              />
            </svg>
            {t('templates')}
          </button>
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm shadow-violet-200"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            {t('newRule')}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-center sm:justify-start gap-1.5 sm:gap-2">
        {/* Rule type chips */}
        {RULE_TYPES.map((ruleType) => {
          const isActive = filters.rule_type === ruleType;
          const label = ruleType
            ? t(`ruleType_${ruleType}`)
            : tCommon('all');
          return (
            <button
              key={ruleType ?? 'all'}
              onClick={() => setRuleType(ruleType)}
              className={`px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-medium transition-all ${
                isActive
                  ? 'bg-violet-50 text-violet-700 ring-1 ring-violet-600/20'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
            </button>
          );
        })}

        {/* Separator */}
        <span className="hidden sm:block text-gray-300 select-none">·</span>

        {/* Active/Inactive filter */}
        {[
          { value: true, label: t('filterActive') },
          { value: false, label: t('filterInactive') },
        ].map((opt) => (
          <button
            key={String(opt.value)}
            onClick={() =>
              setActiveFilter(
                activeFilterValue === opt.value
                  ? undefined
                  : (opt.value as boolean),
              )
            }
            className={`px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-medium transition-all ${
              activeFilterValue === opt.value
                ? 'bg-violet-50 text-violet-700 ring-1 ring-violet-600/20'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && rules.length === 0 && (
        <div className="text-center py-20">
          <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {t('emptyState')}
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            {t('emptyStateSubtitle')}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleCreate}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm shadow-violet-200"
            >
              {t('createFirst')}
            </button>
            <button
              onClick={() => setShowTemplates(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 text-sm font-medium text-gray-700 rounded-xl hover:bg-gray-50 transition-all"
            >
              {t('useTemplate')}
            </button>
          </div>
        </div>
      )}

      {/* Rules list */}
      {!isLoading && rules.length > 0 && (
        <div className="space-y-4">
          <p className="text-xs text-gray-500">
            {count} {count === 1 ? 'pravilo' : count < 5 ? 'pravila' : 'pravila'}
          </p>
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              t={t}
              onEdit={() => handleEdit(rule)}
              onDelete={() => setShowDeleteConfirm(rule)}
              onHistory={() => setShowHistory(rule)}
              onToggleActive={(active) => toggleActive(rule.id, active)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {showForm && (
        <RuleFormModal
          rule={editingRule}
          template={templateData}
          t={t}
          tCommon={tCommon}
          tDetail={tDetail}
          onSave={handleFormSave}
          onClose={() => {
            setShowForm(false);
            setEditingRule(null);
            setTemplateData(null);
          }}
        />
      )}

      {showTemplates && (
        <TemplatesModal
          t={t}
          onApply={handleApplyTemplate}
          onClose={() => setShowTemplates(false)}
        />
      )}

      {showDeleteConfirm && (
        <DeleteConfirmModal
          rule={showDeleteConfirm}
          t={t}
          tCommon={tCommon}
          onConfirm={handleDelete}
          onClose={() => setShowDeleteConfirm(null)}
        />
      )}

      {showHistory && (
        <ExecutionHistoryModal
          rule={showHistory}
          t={t}
          onClose={() => setShowHistory(null)}
        />
      )}
    </div>
  );
}

// ── RuleCard ───────────────────────────────────────────────────────────────────

function RuleCard({
  rule,
  t,
  onEdit,
  onDelete,
  onHistory,
  onToggleActive,
}: {
  rule: AutomationRuleResponse;
  t: TranslationFn;
  onEdit: () => void;
  onDelete: () => void;
  onHistory: () => void;
  onToggleActive: (active: boolean) => void;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 hover:shadow-md transition-shadow">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <h3 className="text-base font-semibold text-gray-900 truncate">
            {rule.name}
          </h3>
          <span
            className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ring-1 ${RULE_TYPE_COLORS[rule.rule_type]}`}
          >
            {t(`ruleType_${rule.rule_type}`)}
          </span>
          <span className="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-50 text-gray-600">
            {t('priority')} {rule.priority}
          </span>
        </div>
        <button
          onClick={() => onToggleActive(!rule.is_active)}
          className={`shrink-0 relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            rule.is_active ? 'bg-violet-600' : 'bg-gray-200'
          }`}
          title={rule.is_active ? t('active') : t('inactive')}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
              rule.is_active ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Description */}
      {rule.description && (
        <p className="mt-2 text-sm text-gray-500">{rule.description}</p>
      )}

      {/* Conditions & Actions summary */}
      <div className="mt-3 space-y-2">
        <div className="flex items-start gap-2">
          <span className="shrink-0 text-xs font-medium text-gray-400 w-14 pt-0.5">
            {t('conditions')}
          </span>
          <p className="text-sm text-gray-700">
            {summarizeConditions(rule.conditions, t)}
          </p>
        </div>
        <div className="flex items-start gap-2">
          <span className="shrink-0 text-xs font-medium text-gray-400 w-14 pt-0.5">
            {t('actions')}
          </span>
          <p className="text-sm text-gray-700">
            {summarizeActions(rule.actions, t)}
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span>
            {t('executionCount', { count: rule.execution_count })}
          </span>
          <span>
            {rule.last_executed_at
              ? t('lastExecuted', {
                  date: formatRelativeTime(rule.last_executed_at),
                })
              : t('neverExecuted')}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onHistory}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
            title={t('history')}
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
                strokeWidth={1.75}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
          <button
            onClick={onEdit}
            className="p-2 rounded-lg text-gray-400 hover:text-violet-600 hover:bg-violet-50 transition-colors"
            title={t('editRule')}
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
                strokeWidth={1.75}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </button>
          <button
            onClick={onDelete}
            className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            title={t('deleteRule')}
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
                strokeWidth={1.75}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// ── RuleFormModal ──────────────────────────────────────────────────────────────

interface FormCondition {
  field: string;
  operator: ConditionOperator;
  value: string;
  value2: string; // for 'between'
}

interface FormAction {
  type: ActionType;
  target: string;
  value: string;
  description: string;
  reason: string;
}

function RuleFormModal({
  rule,
  template,
  t,
  tCommon,
  tDetail,
  onSave,
  onClose,
}: {
  rule: AutomationRuleResponse | null;
  template: RuleTemplate | null;
  t: TranslationFn;
  tCommon: TranslationFn;
  tDetail: TranslationFn;
  onSave: (data: AutomationRuleCreate | AutomationRuleUpdate) => Promise<void>;
  onClose: () => void;
}) {
  const source = rule || template;
  const [name, setName] = useState(source?.name ?? '');
  const [description, setDescription] = useState(
    (rule?.description ?? template?.description) || '',
  );
  const [ruleType, setRuleTypeState] = useState<RuleType>(
    source?.rule_type ?? 'KONTO_ASSIGNMENT',
  );
  const [priority, setPriority] = useState(source?.priority ?? 50);
  const [logicOperator, setLogicOperator] = useState<'AND' | 'OR'>(
    source?.conditions?.operator ?? 'AND',
  );
  const [conditions, setConditions] = useState<FormCondition[]>(() =>
    parseConditions(source?.conditions),
  );
  const [actions, setActions] = useState<FormAction[]>(() =>
    parseActions(source?.actions),
  );
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function parseConditions(
    cg: ConditionGroup | undefined | null,
  ): FormCondition[] {
    if (!cg || !cg.rules || cg.rules.length === 0)
      return [{ field: 'seller.pib', operator: 'equals', value: '', value2: '' }];
    return cg.rules
      .filter((r): r is ConditionRule => 'field' in r)
      .map((r) => ({
        field: r.field,
        operator: r.operator,
        value:
          r.operator === 'between' && Array.isArray(r.value)
            ? String(r.value[0] ?? '')
            : r.operator === 'in' || r.operator === 'not_in'
              ? Array.isArray(r.value)
                ? r.value.join(', ')
                : String(r.value ?? '')
              : String(r.value ?? ''),
        value2:
          r.operator === 'between' && Array.isArray(r.value)
            ? String(r.value[1] ?? '')
            : '',
      }));
  }

  function parseActions(
    acts: RuleAction[] | undefined | null,
  ): FormAction[] {
    if (!acts || acts.length === 0)
      return [
        { type: 'SET_KONTO', target: 'debit', value: '', description: '', reason: '' },
      ];
    return acts.map((a) => ({
      type: a.type,
      target: String(a.target ?? ''),
      value: String(a.value ?? ''),
      description: a.description ?? '',
      reason: a.reason ?? '',
    }));
  }

  function addCondition() {
    setConditions((prev) => [
      ...prev,
      { field: 'seller.pib', operator: 'equals', value: '', value2: '' },
    ]);
  }

  function removeCondition(index: number) {
    setConditions((prev) => prev.filter((_, i) => i !== index));
  }

  function updateCondition(
    index: number,
    patch: Partial<FormCondition>,
  ) {
    setConditions((prev) =>
      prev.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    );
  }

  function addAction() {
    setActions((prev) => [
      ...prev,
      { type: 'SET_KONTO', target: 'debit', value: '', description: '', reason: '' },
    ]);
  }

  function removeAction(index: number) {
    setActions((prev) => prev.filter((_, i) => i !== index));
  }

  function updateAction(
    index: number,
    patch: Partial<FormAction>,
  ) {
    setActions((prev) =>
      prev.map((a, i) => (i === index ? { ...a, ...patch } : a)),
    );
  }

  async function handleSubmit() {
    setFormError(null);
    if (!name.trim()) {
      setFormError(t('ruleName'));
      return;
    }
    if (conditions.length === 0) {
      setFormError(t('addCondition'));
      return;
    }
    if (actions.length === 0) {
      setFormError(t('addAction'));
      return;
    }

    const conditionRules: ConditionRule[] = conditions.map((c) => {
      let value: unknown = c.value;
      if (c.operator === 'between') {
        value = [
          isNaN(Number(c.value)) ? c.value : Number(c.value),
          isNaN(Number(c.value2)) ? c.value2 : Number(c.value2),
        ];
      } else if (c.operator === 'in' || c.operator === 'not_in') {
        value = c.value.split(',').map((v) => v.trim());
      } else if (c.operator === 'is_null' || c.operator === 'is_not_null') {
        value = null;
      } else if (!isNaN(Number(c.value)) && c.value.trim() !== '') {
        const fieldType = getFieldType(c.field);
        if (fieldType === 'numeric') value = Number(c.value);
      }
      return { field: c.field, operator: c.operator, value };
    });

    const ruleActions: RuleAction[] = actions.map((a) => {
      const action: RuleAction = { type: a.type };
      if (a.type === 'SET_KONTO') {
        action.target = a.target;
        action.value = a.value;
        if (a.description) action.description = a.description;
      } else if (a.type === 'SET_VAT_TREATMENT') {
        action.value = a.value;
      } else if (a.type === 'FLAG_REVIEW') {
        if (a.reason) action.reason = a.reason;
      } else if (a.type === 'SET_CUSTOM_FIELD') {
        action.target = a.target;
        action.value = a.value;
      }
      return action;
    });

    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      rule_type: ruleType,
      priority,
      conditions: {
        operator: logicOperator,
        rules: conditionRules,
      },
      actions: ruleActions,
      is_active: true,
    };

    setSaving(true);
    try {
      await onSave(payload);
    } catch {
      setFormError('Greška pri čuvanju pravila');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {rule ? t('editRule') : t('createRule')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="px-6 py-5 space-y-6 max-h-[calc(100vh-12rem)] overflow-y-auto">
          {/* Basic info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('ruleName')} *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                placeholder={t('ruleName')}
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('ruleDescription')}
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                placeholder={t('ruleDescription')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('ruleTypeLabel')}
              </label>
              <select
                value={ruleType}
                onChange={(e) => setRuleTypeState(e.target.value as RuleType)}
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent bg-white"
              >
                {RULE_TYPES.filter(Boolean).map((rt) => (
                  <option key={rt} value={rt}>
                    {t(`ruleType_${rt}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('priority')}
              </label>
              <input
                type="number"
                min={1}
                max={1000}
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Conditions */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900">
                {t('conditions')}
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setLogicOperator('AND')}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                    logicOperator === 'AND'
                      ? 'bg-violet-100 text-violet-700'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}
                >
                  {t('allConditions')}
                </button>
                <button
                  onClick={() => setLogicOperator('OR')}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                    logicOperator === 'OR'
                      ? 'bg-violet-100 text-violet-700'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}
                >
                  {t('anyCondition')}
                </button>
              </div>
            </div>
            <div className="space-y-3">
              {conditions.map((cond, idx) => (
                <ConditionRow
                  key={idx}
                  condition={cond}
                  t={t}
                  onChange={(patch) => updateCondition(idx, patch)}
                  onRemove={
                    conditions.length > 1
                      ? () => removeCondition(idx)
                      : undefined
                  }
                />
              ))}
            </div>
            <button
              onClick={addCondition}
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-violet-600 hover:text-violet-700 font-medium"
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
                  d="M12 4v16m8-8H4"
                />
              </svg>
              {t('addCondition')}
            </button>
          </div>

          {/* Actions */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              {t('actions')}
            </h3>
            <div className="space-y-3">
              {actions.map((action, idx) => (
                <ActionRow
                  key={idx}
                  action={action}
                  t={t}
                  tDetail={tDetail}
                  onChange={(patch) => updateAction(idx, patch)}
                  onRemove={
                    actions.length > 1
                      ? () => removeAction(idx)
                      : undefined
                  }
                />
              ))}
            </div>
            <button
              onClick={addAction}
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-violet-600 hover:text-violet-700 font-medium"
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
                  d="M12 4v16m8-8H4"
                />
              </svg>
              {t('addAction')}
            </button>
          </div>

          {/* Form error */}
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {formError}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-xl transition-colors"
          >
            {tCommon('cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-5 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-sm shadow-violet-200 disabled:opacity-50"
          >
            {saving
              ? tCommon('saving')
              : rule
                ? t('updateRule')
                : t('createRule')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ConditionRow ───────────────────────────────────────────────────────────────

function ConditionRow({
  condition,
  t,
  onChange,
  onRemove,
}: {
  condition: FormCondition;
  t: TranslationFn;
  onChange: (patch: Partial<FormCondition>) => void;
  onRemove?: () => void;
}) {
  const fieldType = getFieldType(condition.field);
  const operators = getOperatorsForType(fieldType);
  const noValue =
    condition.operator === 'is_null' || condition.operator === 'is_not_null';
  const isBetween = condition.operator === 'between';

  return (
    <div className="flex items-start gap-2 p-3 bg-gray-50 rounded-xl">
      {/* Field select */}
      <select
        value={condition.field}
        onChange={(e) => {
          const newField = e.target.value;
          const newType = getFieldType(newField);
          const newOps = getOperatorsForType(newType);
          const op = newOps.includes(condition.operator)
            ? condition.operator
            : newOps[0];
          onChange({ field: newField, operator: op });
        }}
        className="px-2 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500 min-w-[160px]"
      >
        {FIELD_GROUPS.map((group) => (
          <optgroup key={group.labelKey} label={t(group.labelKey)}>
            {group.fields.map((f) => (
              <option key={f.value} value={f.value}>
                {f.labelKey}
              </option>
            ))}
          </optgroup>
        ))}
      </select>

      {/* Operator select */}
      <select
        value={condition.operator}
        onChange={(e) =>
          onChange({ operator: e.target.value as ConditionOperator })
        }
        className="px-2 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500 min-w-[130px]"
      >
        {operators.map((op) => (
          <option key={op} value={op}>
            {t(`op_${op}`)}
          </option>
        ))}
      </select>

      {/* Value input(s) */}
      {!noValue && (
        <>
          <input
            type={fieldType === 'numeric' ? 'number' : 'text'}
            value={condition.value}
            onChange={(e) => onChange({ value: e.target.value })}
            placeholder={t('valueLabel')}
            className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 min-w-[100px]"
          />
          {isBetween && (
            <>
              <span className="text-sm text-gray-400 self-center">—</span>
              <input
                type={fieldType === 'numeric' ? 'number' : 'text'}
                value={condition.value2}
                onChange={(e) => onChange({ value2: e.target.value })}
                placeholder={t('valueLabel')}
                className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 min-w-[100px]"
              />
            </>
          )}
        </>
      )}

      {/* Remove button */}
      {onRemove && (
        <button
          onClick={onRemove}
          className="shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
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
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}

// ── ActionRow ──────────────────────────────────────────────────────────────────

function ActionRow({
  action,
  t,
  tDetail,
  onChange,
  onRemove,
}: {
  action: FormAction;
  t: TranslationFn;
  tDetail: TranslationFn;
  onChange: (patch: Partial<FormAction>) => void;
  onRemove?: () => void;
}) {
  const ACTION_TYPES: ActionType[] = [
    'SET_KONTO',
    'SET_VAT_TREATMENT',
    'FLAG_REVIEW',
    'AUTO_APPROVE',
    'SET_CUSTOM_FIELD',
  ];

  return (
    <div className="p-3 bg-gray-50 rounded-xl space-y-2">
      <div className="flex items-center gap-2">
        <select
          value={action.type}
          onChange={(e) => onChange({ type: e.target.value as ActionType })}
          className="px-2 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
        >
          {ACTION_TYPES.map((at) => (
            <option key={at} value={at}>
              {at === 'SET_KONTO'
                ? t('ruleType_KONTO_ASSIGNMENT')
                : at === 'SET_VAT_TREATMENT'
                  ? t('ruleType_VAT_TREATMENT')
                  : at === 'FLAG_REVIEW'
                    ? t('ruleType_FLAG_FOR_REVIEW')
                    : at === 'AUTO_APPROVE'
                      ? t('ruleType_AUTO_APPROVE')
                      : t('ruleType_CUSTOM_FIELD')}
            </option>
          ))}
        </select>
        {onRemove && (
          <button
            onClick={onRemove}
            className="ml-auto shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Type-specific fields */}
      {action.type === 'SET_KONTO' && (
        <div className="flex items-center gap-2">
          <select
            value={action.target}
            onChange={(e) => onChange({ target: e.target.value })}
            className="px-2 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
          >
            <option value="debit">{t('debitSide')}</option>
            <option value="credit">{t('creditSide')}</option>
          </select>
          <input
            type="text"
            value={action.value}
            onChange={(e) => onChange({ value: e.target.value })}
            placeholder={t('kontoValue')}
            className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
          <input
            type="text"
            value={action.description}
            onChange={(e) => onChange({ description: e.target.value })}
            placeholder={t('kontoDescription')}
            className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      )}

      {action.type === 'SET_VAT_TREATMENT' && (
        <select
          value={action.value}
          onChange={(e) => onChange({ value: e.target.value })}
          className="w-full px-2 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500"
        >
          <option value="">{t('vatValue')}</option>
          {VAT_TREATMENT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {tDetail(opt.labelKey)}
            </option>
          ))}
        </select>
      )}

      {action.type === 'FLAG_REVIEW' && (
        <input
          type="text"
          value={action.reason}
          onChange={(e) => onChange({ reason: e.target.value })}
          placeholder={t('flagReason')}
          className="w-full px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
      )}

      {action.type === 'SET_CUSTOM_FIELD' && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={action.target}
            onChange={(e) => onChange({ target: e.target.value })}
            placeholder={t('customFieldName')}
            className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
          <input
            type="text"
            value={action.value}
            onChange={(e) => onChange({ value: e.target.value })}
            placeholder={t('customFieldValue')}
            className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      )}
    </div>
  );
}

// ── TemplatesModal ─────────────────────────────────────────────────────────────

function TemplatesModal({
  t,
  onApply,
  onClose,
}: {
  t: TranslationFn;
  onApply: (tmpl: RuleTemplate) => void;
  onClose: () => void;
}) {
  const [templates, setTemplates] = useState<RuleTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuleTemplates()
      .then(setTemplates)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const TEMPLATE_ICONS: Record<string, string> = {
    fuel_non_deductible: 'M13 10V3L4 14h7v7l9-11h-7z',
    telecom_expenses:
      'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
    office_supplies:
      'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    professional_services:
      'M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    utilities:
      'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    rent_payments:
      'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
    large_invoice_review:
      'M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    new_supplier_review:
      'M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z',
    foreign_supplier_review:
      'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl my-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {t('templateGallery')}
            </h2>
            <p className="text-sm text-gray-500">
              {t('templateGallerySubtitle')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map((tmpl) => {
                const iconPath =
                  TEMPLATE_ICONS[tmpl.name] || TEMPLATE_ICONS['office_supplies'];
                return (
                  <div
                    key={tmpl.name}
                    className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-violet-200 hover:bg-violet-50/30 transition-all"
                  >
                    <div className="w-10 h-10 bg-violet-100 rounded-xl flex items-center justify-center mb-3 mx-auto sm:mx-0">
                      <svg
                        className="w-5 h-5 text-violet-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.75}
                          d={iconPath}
                        />
                      </svg>
                    </div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-1 text-center sm:text-left">
                      {tmpl.description}
                    </h3>
                    <p className="text-xs text-gray-500 mb-3 text-center sm:text-left">
                      {t(`ruleType_${tmpl.rule_type}`)}
                    </p>
                    <button
                      onClick={() => onApply(tmpl)}
                      className="w-full px-3 py-1.5 text-xs font-medium text-violet-700 bg-violet-100 rounded-lg hover:bg-violet-200 transition-colors"
                    >
                      {t('useThisTemplate')}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── ExecutionHistoryModal ──────────────────────────────────────────────────────

function ExecutionHistoryModal({
  rule,
  t,
  onClose,
}: {
  rule: AutomationRuleResponse;
  t: TranslationFn;
  onClose: () => void;
}) {
  const execOrgPath = useOrgPath();
  const [executions, setExecutions] = useState<RuleExecutionResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuleExecutions(rule.id)
      .then(setExecutions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [rule.id]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {t('executionHistory')}
            </h2>
            <p className="text-sm text-gray-500">{rule.name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-6 max-h-[calc(100vh-12rem)] overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
            </div>
          ) : executions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-sm text-gray-500">{t('noExecutions')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {executions.map((exec) => (
                <div
                  key={exec.id}
                  className="p-4 bg-gray-50 rounded-xl border border-gray-100"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-900">
                      {formatDateSr(exec.executed_at)}{' '}
                      <span className="text-gray-400 font-normal">
                        {new Date(exec.executed_at).toLocaleTimeString(
                          'sr-Latn-RS',
                          { hour: '2-digit', minute: '2-digit' },
                        )}
                      </span>
                    </span>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      {exec.execution_time_ms !== null && (
                        <span>{exec.execution_time_ms}ms</span>
                      )}
                      <Link
                        href={execOrgPath(`/invoices/${exec.invoice_id}`)}
                        className="text-violet-600 hover:text-violet-700 font-medium"
                      >
                        {t('invoiceLink')}
                      </Link>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    <span className="font-medium text-gray-600">
                      {t('actionsApplied')}:
                    </span>{' '}
                    {exec.actions_applied
                      .map((a: RuleAction) => a.type)
                      .join(', ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── DeleteConfirmModal ─────────────────────────────────────────────────────────

function DeleteConfirmModal({
  rule,
  t,
  tCommon,
  onConfirm,
  onClose,
}: {
  rule: AutomationRuleResponse;
  t: TranslationFn;
  tCommon: TranslationFn;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleConfirm() {
    setDeleting(true);
    try {
      await onConfirm();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-6 h-6 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
          {t('deleteConfirmTitle')}
        </h3>
        <p className="text-sm text-gray-500 text-center mb-6">
          {t('deleteConfirmMessage', { name: rule.name })}
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-xl transition-colors"
          >
            {tCommon('cancel')}
          </button>
          <button
            onClick={handleConfirm}
            disabled={deleting}
            className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            {deleting ? tCommon('deleting') : tCommon('delete')}
          </button>
        </div>
      </div>
    </div>
  );
}
