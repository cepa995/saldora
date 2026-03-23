import { useTranslations } from 'next-intl';

interface ConfidenceBadgeProps {
  confidence: number | null;
  className?: string;
}

/**
 * Inline confidence indicator with colored dot and text label.
 *
 * >=85%: Pouzdano (green), 65-84%: Proveriti (amber), <65%: Nepouzdano (red), null: gray dash.
 */
export function ConfidenceBadge({ confidence, className = '' }: ConfidenceBadgeProps) {
  const t = useTranslations('common');

  if (confidence === null || confidence === undefined) {
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs text-gray-400 ${className}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
        —
      </span>
    );
  }

  const rounded = Math.round(confidence);
  let dotClass: string;
  let textClass: string;
  let label: string;

  if (rounded >= 75) {
    dotClass = 'bg-green-500';
    textClass = 'text-green-700';
    label = t('confidenceReliable');
  } else if (rounded >= 50) {
    dotClass = 'bg-amber-500';
    textClass = 'text-amber-700';
    label = t('confidenceReview');
  } else {
    dotClass = 'bg-red-500';
    textClass = 'text-red-700';
    label = t('confidenceUnreliable');
  }

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${textClass} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
      {label}
    </span>
  );
}
