import { getRequestConfig } from 'next-intl/server';
import { cookies } from 'next/headers';
import { type Locale, locales, defaultLocale } from './config';

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get('saldora_locale')?.value;
  const locale: Locale = locales.includes(raw as Locale) ? (raw as Locale) : defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
