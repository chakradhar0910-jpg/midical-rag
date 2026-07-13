'use client';
import { useI18n, Locale } from '@/i18n/context';
import { Globe } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

export function LanguageSelector({ className }: { className?: string }) {
  const { locale, setLocale, localeNames, localeFlags, locales } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border bg-background hover:bg-muted transition-colors text-sm font-medium"
        title="Change Language"
      >
        <Globe className="w-4 h-4 text-muted-foreground" />
        <span>{localeFlags[locale]}</span>
        <span className="hidden sm:inline">{localeNames[locale]}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-40 bg-card border rounded-xl shadow-lg overflow-hidden z-50">
          {locales.map((loc) => (
            <button
              key={loc}
              onClick={() => { setLocale(loc as Locale); setOpen(false); }}
              className={cn(
                'w-full flex items-center gap-2.5 px-3 py-2.5 text-sm hover:bg-muted transition-colors text-left',
                locale === loc && 'bg-primary/10 text-primary font-medium'
              )}
            >
              <span className="text-base">{localeFlags[loc as Locale]}</span>
              <span>{localeNames[loc as Locale]}</span>
              {locale === loc && <span className="ml-auto text-primary text-xs">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
