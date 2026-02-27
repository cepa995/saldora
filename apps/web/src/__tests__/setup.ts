import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock next-intl — returns the key itself for easy assertion
vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string, params?: Record<string, string>) => {
      if (params) {
        let result = key;
        for (const [k, v] of Object.entries(params)) {
          result += `_${k}:${v}`;
        }
        return result;
      }
      return key;
    };
    return t;
  },
  useLocale: () => 'sr-Latn',
}));

// Mock next-intl/server
vi.mock('next-intl/server', () => ({
  getTranslations: async () => {
    const t = (key: string, params?: Record<string, string>) => {
      if (params) {
        let result = key;
        for (const [k, v] of Object.entries(params)) {
          result += `_${k}:${v}`;
        }
        return result;
      }
      return key;
    };
    return t;
  },
}));
