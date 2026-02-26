'use client';

import { ConfidenceBadge } from './ConfidenceBadge';

interface EditableFieldProps {
  label: string;
  value: string | null;
  onChange: (value: string) => void;
  confidence?: number | null;
  disabled?: boolean;
  type?: 'text' | 'date' | 'number';
}

/**
 * Inline-editable field with label and optional confidence indicator.
 */
export function EditableField({
  label,
  value,
  onChange,
  confidence,
  disabled = false,
  type = 'text',
}: EditableFieldProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <label className="text-xs font-medium text-gray-500">{label}</label>
        {confidence !== undefined && confidence !== null && (
          <ConfidenceBadge confidence={confidence} />
        )}
      </div>
      <input
        type={type}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-shadow ${
          disabled ? 'bg-gray-50 text-gray-500 cursor-not-allowed' : ''
        }`}
      />
    </div>
  );
}
