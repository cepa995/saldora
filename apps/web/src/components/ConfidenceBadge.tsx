interface ConfidenceBadgeProps {
  confidence: number | null;
  className?: string;
}

/**
 * Inline confidence score indicator with colored dot and percentage.
 *
 * Green (>=80%), Amber (60-79%), Red (<60%), Gray (null).
 */
export function ConfidenceBadge({ confidence, className = '' }: ConfidenceBadgeProps) {
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

  if (rounded >= 80) {
    dotClass = 'bg-green-500';
    textClass = 'text-green-700';
  } else if (rounded >= 60) {
    dotClass = 'bg-amber-500';
    textClass = 'text-amber-700';
  } else {
    dotClass = 'bg-red-500';
    textClass = 'text-red-700';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${textClass} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
      {rounded}%
    </span>
  );
}
