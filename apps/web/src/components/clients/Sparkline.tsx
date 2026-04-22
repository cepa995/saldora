'use client';

interface Props {
  /** Bars are rendered in order — oldest on the left, current on the right. */
  values: number[];
  /** Width in px (the SVG keeps a fixed aspect ratio). */
  width?: number;
  height?: number;
  /** Tailwind fill class for normal bars. */
  barClassName?: string;
  /** Tailwind fill class for the rightmost (current-period) bar. */
  currentBarClassName?: string;
  /** Accessible label for the whole series, e.g. "Trend poslednjih 6 meseci". */
  ariaLabel?: string;
}

/**
 * Tiny bar sparkline. Shows the current period in a brighter tint so the
 * eye anchors there, then the five months behind it in a muted tone. If
 * every value is zero we render flat placeholder bars — the axis is stable
 * across cards regardless of data density.
 */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  barClassName = 'fill-stone-300',
  currentBarClassName = 'fill-violet-500',
  ariaLabel,
}: Props) {
  const n = values.length;
  if (n === 0) return null;

  const max = Math.max(...values, 1);
  const gap = 2;
  const barWidth = (width - gap * (n - 1)) / n;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel}
      className="shrink-0"
    >
      {values.map((v, i) => {
        const isCurrent = i === n - 1;
        // Minimum visible nub (2px) so a 0 isn't a bare axis. Distinguishable
        // from a real small value because it sits on the baseline only.
        const barHeight = v === 0 ? 2 : Math.max(2, Math.round((v / max) * (height - 2)));
        const x = i * (barWidth + gap);
        const y = height - barHeight;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barWidth}
            height={barHeight}
            rx={1}
            className={isCurrent ? currentBarClassName : barClassName}
          />
        );
      })}
    </svg>
  );
}
