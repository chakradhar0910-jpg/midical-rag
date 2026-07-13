'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Activity, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useI18n } from '@/i18n/context';
import { LanguageSelector } from '@/components/layout/LanguageSelector';

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password required'),
  mfa_token: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const { t } = useI18n();
  const [showPassword, setShowPassword] = useState(false);
  const [requiresMFA, setRequiresMFA] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      await login(data.email, data.password, data.mfa_token);
      toast.success(t('auth.loginSuccess'));
      router.push('/dashboard');
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || t('errors.generic');
      if (status === 428) { setRequiresMFA(true); toast.error(t('auth.mfaRequired')); }
      else toast.error(detail);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-md">
        <div className="bg-card rounded-2xl border shadow-sm p-8">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <span className="font-bold text-xl">MedicalRAG</span>
            </div>
            <LanguageSelector />
          </div>

          <h1 className="text-2xl font-bold text-center mb-2">{t('auth.welcomeBack')}</h1>
          <p className="text-muted-foreground text-center text-sm mb-8">{t('auth.signInDesc')}</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1.5 block">{t('auth.email')}</label>
              <input {...register('email')} type="email" placeholder="doctor@hospital.com"
                className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
              {errors.email && <p className="text-destructive text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <div className="flex justify-between mb-1.5">
                <label className="text-sm font-medium">{t('auth.password')}</label>
                <Link href="/auth/reset-password" className="text-xs text-primary hover:underline">{t('auth.forgotPassword')}</Link>
              </div>
              <div className="relative">
                <input {...register('password')} type={showPassword ? 'text' : 'password'} placeholder="••••••••"
                  className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 pr-10" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-destructive text-xs mt-1">{errors.password.message}</p>}
            </div>
            {requiresMFA && (
              <div>
                <label className="text-sm font-medium mb-1.5 block">{t('auth.mfaCode')}</label>
                <input {...register('mfa_token')} type="text" placeholder="123456" maxLength={6}
                  className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 text-center tracking-widest" />
              </div>
            )}
            <button type="submit" disabled={isLoading}
              className="w-full bg-primary text-white font-semibold py-2.5 rounded-lg hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-60">
              {isLoading ? <><Loader2 className="w-4 h-4 animate-spin" />{t('common.loading')}</> : t('auth.login')}
            </button>
          </form>

          <div className="mt-4 p-3 bg-muted rounded-lg text-xs text-muted-foreground">
            <p className="font-medium text-foreground mb-1">{t('auth.demoCredentials')}:</p>
            <p>Admin: admin@medicalrag.com / Admin@123456</p>
            <p>User: user1@medicalrag.com / User@123456</p>
          </div>

          <p className="text-center text-sm text-muted-foreground mt-6">
            {t('auth.noAccount')}{' '}
            <Link href="/auth/register" className="text-primary font-medium hover:underline">{t('auth.signUp')}</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
