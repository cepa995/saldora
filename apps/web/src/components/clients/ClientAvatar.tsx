'use client';

const GRADIENTS = [
  'from-violet-500 to-indigo-600',
  'from-rose-500 to-orange-500',
  'from-emerald-500 to-teal-600',
  'from-amber-500 to-red-500',
  'from-sky-500 to-indigo-600',
  'from-fuchsia-500 to-pink-600',
  'from-lime-500 to-emerald-600',
];

function hashToIndex(seed: string, mod: number): number {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) {
    h = (h << 5) - h + seed.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h) % mod;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

interface Props {
  name: string;
  seed?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const SIZE_CLS: Record<NonNullable<Props['size']>, string> = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-base',
  xl: 'w-16 h-16 text-lg sm:w-20 sm:h-20 sm:text-xl',
};

export function ClientAvatar({ name, seed, size = 'md', className = '' }: Props) {
  const gradient = GRADIENTS[hashToIndex(seed ?? name, GRADIENTS.length)];
  return (
    <div
      className={`inline-flex items-center justify-center rounded-2xl bg-gradient-to-br ${gradient} text-white font-bold shadow-sm ring-1 ring-black/5 shrink-0 ${SIZE_CLS[size]} ${className}`}
      aria-hidden="true"
    >
      {initials(name)}
    </div>
  );
}
