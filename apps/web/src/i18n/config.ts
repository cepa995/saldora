export const locales = ['sr-Latn', 'sr-Cyrl', 'en'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'sr-Latn';
