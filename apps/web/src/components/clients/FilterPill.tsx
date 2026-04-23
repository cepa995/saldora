'use client';

export type PillTone =
  | 'neutral'
  | 'amber'
  | 'emerald'
  | 'rose'
  | 'violet'
  | 'blue';

interface Props {
  label: string;
  count?: number;
  active: boolean;
  tone?: PillTone;
  onClick: () => void;
}

const TONES: Record<
  PillTone,
  { ring: string; shadow: string; text: string; badge: string; dot: string }
> = {
  neutral: {
    ring: 'ring-stone-300',
    shadow: 'shadow-stone-900/[0.03]',
    text: 'text-stone-900',
    badge: 'bg-stone-100 text-stone-700',
    dot: '',
  },
  amber: {
    ring: 'ring-amber-300',
    shadow: 'shadow-amber-600/[0.06]',
    text: 'text-amber-800',
    badge: 'bg-amber-100 text-amber-800',
    dot: 'bg-amber-500',
  },
  emerald: {
    ring: 'ring-emerald-300',
    shadow: 'shadow-emerald-600/[0.06]',
    text: 'text-emerald-800',
    badge: 'bg-emerald-100 text-emerald-800',
    dot: 'bg-emerald-500',
  },
  rose: {
    ring: 'ring-rose-300',
    shadow: 'shadow-rose-600/[0.06]',
    text: 'text-rose-800',
    badge: 'bg-rose-100 text-rose-800',
    dot: 'bg-rose-500',
  },
  violet: {
    ring: 'ring-violet-300',
    shadow: 'shadow-violet-600/[0.06]',
    text: 'text-violet-800',
    badge: 'bg-violet-100 text-violet-800',
    dot: 'bg-violet-500',
  },
  blue: {
    ring: 'ring-blue-300',
    shadow: 'shadow-blue-600/[0.06]',
    text: 'text-blue-800',
    badge: 'bg-blue-100 text-blue-800',
    dot: 'bg-blue-500',
  },
};

export function FilterPill({ label, count, active, tone = 'neutral', onClick }: Props) {
  const t = TONES[tone];
  const activeCls = `bg-white ${t.text} ring-1 ${t.ring} shadow-sm ${t.shadow}`;
  const inactiveCls =
    'bg-stone-100 text-stone-700 hover:bg-stone-200/80 ring-1 ring-transparent';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 h-9 px-3.5 text-sm font-medium rounded-full transition-all ${
        active ? activeCls : inactiveCls
      }`}
    >
      {t.dot && (
        <span className={`w-1.5 h-1.5 rounded-full ${t.dot}`} aria-hidden="true" />
      )}
      <span>{label}</span>
      {typeof count === 'number' && (
        <span
          className={`tabular-nums px-1.5 min-w-[1.25rem] h-5 inline-flex items-center justify-center text-[11px] rounded-full ${
            active ? t.badge : 'bg-white text-stone-500'
          }`}
        >
          {count}
        </span>
      )}
    </button>
  );
}
