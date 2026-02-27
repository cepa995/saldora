'use client';

import { ConfidenceBadge } from './ConfidenceBadge';

interface EditableFieldProps {
  label: string;
  value: string | null;
  onChange: (value: string) => void;
  confidence?: number | null;
  disabled?: boolean;
  type?: 'text' | 'date' | 'number';
  isDirty?: boolean;
  onReset?: () => void;
  /** Validation issue severity — 'error' for red, 'warning' for amber */
  validationStatus?: 'error' | 'warning';
}

/**
 * Inline-editable field with label, optional confidence indicator,
 * dirty-state highlight, validation status, and per-field reset.
 */
export function EditableField({
  label,
  value,
  onChange,
  confidence,
  disabled = false,
  type = 'text',
  isDirty = false,
  onReset,
  validationStatus,
}: EditableFieldProps) {
  const borderClass = (() => {
    if (disabled) return 'bg-gray-50 text-gray-500 cursor-not-allowed border-gray-200';
    if (validationStatus === 'error') return 'border-red-400 bg-red-50/30 ring-1 ring-red-200';
    if (validationStatus === 'warning') return 'border-amber-400 bg-amber-50/30 ring-1 ring-amber-200';
    if (isDirty) return 'border-violet-400 bg-violet-50/30';
    return 'border-gray-200';
  })();

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <label className={`text-xs font-medium ${
          validationStatus === 'error' ? 'text-red-600' :
          validationStatus === 'warning' ? 'text-amber-600' :
          'text-gray-500'
        }`}>
          {label}
          {validationStatus === 'error' && (
            <svg className="w-3 h-3 inline-block ml-1 -mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          )}
          {validationStatus === 'warning' && (
            <svg className="w-3 h-3 inline-block ml-1 -mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          )}
        </label>
        {confidence !== undefined && confidence !== null && (
          <ConfidenceBadge confidence={confidence} />
        )}
        {isDirty && onReset && (
          <button
            type="button"
            onClick={onReset}
            className="ml-auto p-0.5 text-gray-400 hover:text-violet-600 transition-colors"
            title="Vrati originalno"
            aria-label="Reset to original"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a5 5 0 010 10H9m-6-10l4-4m-4 4l4 4" />
            </svg>
          </button>
        )}
      </div>
      <input
        type={type}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`w-full px-3 py-2 bg-white border rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow ${borderClass}`}
      />
    </div>
  );
}
