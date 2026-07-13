'use client';
import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Cpu, Cloud, Sparkles, ChevronDown, CircleCheck, CircleX } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { aiApi } from '@/lib/api';
import { cn } from '@/lib/utils';

type ProviderValue = 'auto' | 'ollama' | 'gemini';

const PROVIDER_META: Record<ProviderValue, { label: string; icon: any; desc: string }> = {
  auto: { label: 'Auto', icon: Sparkles, desc: 'Ollama if available, else Gemini' },
  ollama: { label: 'Ollama (Local)', icon: Cpu, desc: 'Local inference only — no fallback' },
  gemini: { label: 'Gemini (Cloud)', icon: Cloud, desc: 'Cloud inference only — no fallback' },
};

export function ProviderSelector({ className }: { className?: string }) {
  const { aiProvider, setAIProvider } = useChatStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data: health } = useQuery({
    queryKey: ['ai-health'],
    queryFn: () => aiApi.health(),
    refetchInterval: 30000,
    retry: false,
  });

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const ollamaUp = health?.data?.ollama_running ?? null;
  const geminiUp = health?.data?.gemini_available ?? null;
  const models: string[] = health?.data?.available_models ?? [];

  const current = PROVIDER_META[aiProvider];
  const CurrentIcon = current.icon;

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-background hover:bg-muted transition-colors text-sm font-medium"
        title="Select AI Provider"
      >
        <CurrentIcon className="w-4 h-4 text-primary" />
        <span>{current.label}</span>
        <ChevronDown className={cn('w-3.5 h-3.5 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-72 bg-card border rounded-xl shadow-lg overflow-hidden z-50">
          <div className="px-3 py-2 border-b bg-muted/50">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">AI Provider</p>
          </div>

          {(Object.keys(PROVIDER_META) as ProviderValue[]).map((value) => {
            const meta = PROVIDER_META[value];
            const Icon = meta.icon;
            const active = aiProvider === value;
            return (
              <button
                key={value}
                onClick={() => { setAIProvider(value); setOpen(false); }}
                className={cn(
                  'w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-muted transition-colors',
                  active && 'bg-primary/10'
                )}
              >
                <Icon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', active ? 'text-primary' : 'text-muted-foreground')} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={cn('text-sm font-medium', active && 'text-primary')}>{meta.label}</span>
                    {active && <CircleCheck className="w-3.5 h-3.5 text-primary" />}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{meta.desc}</p>
                </div>
              </button>
            );
          })}

          <div className="px-3 py-2 border-t bg-muted/30 space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Ollama status</span>
              <span className={cn('flex items-center gap-1 font-medium', ollamaUp ? 'text-green-600' : 'text-destructive')}>
                {ollamaUp ? <CircleCheck className="w-3 h-3" /> : <CircleX className="w-3 h-3" />}
                {ollamaUp === null ? 'Checking…' : ollamaUp ? 'Running' : 'Offline'}
              </span>
            </div>
            {ollamaUp && models.length > 0 && (
              <p className="text-xs text-muted-foreground truncate">Models: {models.join(', ')}</p>
            )}
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Gemini status</span>
              <span className={cn('flex items-center gap-1 font-medium', geminiUp ? 'text-green-600' : 'text-destructive')}>
                {geminiUp ? <CircleCheck className="w-3 h-3" /> : <CircleX className="w-3 h-3" />}
                {geminiUp === null ? 'Checking…' : geminiUp ? 'Configured' : 'Not configured'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
