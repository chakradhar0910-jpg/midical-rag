'use client';
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type Locale = 'en' | 'hi' | 'te';

const LOCALE_NAMES: Record<Locale, string> = {
  en: 'English',
  hi: 'हिंदी',
  te: 'తెలుగు',
};

const LOCALE_FLAGS: Record<Locale, string> = {
  en: '🇺🇸',
  hi: '🇮🇳',
  te: '🇮🇳',
};

type TranslationValue = string | Record<string, unknown>;
type Translations = Record<string, TranslationValue>;

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, vars?: Record<string, string>) => string;
  localeNames: typeof LOCALE_NAMES;
  localeFlags: typeof LOCALE_FLAGS;
  locales: Locale[];
}

const I18nContext = createContext<I18nContextType | null>(null);

function getNestedValue(obj: Translations, path: string): string {
  const keys = path.split('.');
  let current: TranslationValue = obj;
  for (const key of keys) {
    if (typeof current !== 'object' || current === null) return path;
    current = (current as Record<string, TranslationValue>)[key];
    if (current === undefined) return path;
  }
  return typeof current === 'string' ? current : path;
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('en');
  const [translations, setTranslations] = useState<Translations>({});

  const loadTranslations = useCallback(async (loc: Locale) => {
    try {
      const msgs = await import(`@/messages/${loc}.json`);
      setTranslations(msgs.default || msgs);
    } catch {
      if (loc !== 'en') {
        const msgs = await import(`@/messages/en.json`);
        setTranslations(msgs.default || msgs);
      }
    }
  }, []);

  useEffect(() => {
    const saved = (typeof window !== 'undefined' ? localStorage.getItem('medrag_locale') : null) as Locale | null;
    const initial: Locale = saved && ['en', 'hi', 'te'].includes(saved) ? saved : 'en';
    setLocaleState(initial);
    loadTranslations(initial);
  }, [loadTranslations]);

  const setLocale = useCallback((loc: Locale) => {
    setLocaleState(loc);
    if (typeof window !== 'undefined') localStorage.setItem('medrag_locale', loc);
    loadTranslations(loc);
  }, [loadTranslations]);

  const t = useCallback((key: string, vars?: Record<string, string>): string => {
    let value = getNestedValue(translations, key);
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => {
        value = value.replace(`{${k}}`, v);
      });
    }
    return value;
  }, [translations]);

  return (
    <I18nContext.Provider value={{
      locale, setLocale, t,
      localeNames: LOCALE_NAMES,
      localeFlags: LOCALE_FLAGS,
      locales: ['en', 'hi', 'te'],
    }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within I18nProvider');
  return ctx;
}
