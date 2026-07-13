'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Activity, Eye, EyeOff, Loader2, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

const schema = z.object({
  username: z.string().min(3).max(50).regex(/^[a-zA-Z0-9_]+$/, 'Alphanumeric and underscore only'),
  email: z.string().email('Invalid email'),
  full_name: z.string().min(2, 'Full name required'),
  password: z.string()
    .min(8, 'Minimum 8 characters')
    .regex(/[A-Z]/, 'Needs uppercase')
    .regex(/[a-z]/, 'Needs lowercase')
    .regex(/\d/, 'Needs number')
    .regex(/[!@#$%^&*]/, 'Needs special character'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, { message: 'Passwords do not match', path: ['confirm_password'] });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser, isLoading } = useAuthStore();
  const [showPwd, setShowPwd] = useState(false);
  const [success, setSuccess] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const password = watch('password', '');
  const checks = [
    { label: '8+ characters', ok: password.length >= 8 },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(password) },
    { label: 'Lowercase letter', ok: /[a-z]/.test(password) },
    { label: 'Number', ok: /\d/.test(password) },
    { label: 'Special character', ok: /[!@#$%^&*]/.test(password) },
  ];

  const onSubmit = async (data: FormData) => {
    try {
      await registerUser({ username: data.username, email: data.email, password: data.password, full_name: data.full_name });
      setSuccess(true);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Registration failed');
    }
  };

  if (success) return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="bg-card rounded-2xl border shadow-sm p-8 max-w-md w-full text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Account Created!</h2>
        <p className="text-muted-foreground mb-6">Please check your email to verify your account, then sign in.</p>
        <Link href="/auth/login" className="bg-primary text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-primary/90 transition-colors">Go to Login</Link>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-card rounded-2xl border shadow-sm p-8">
          <div className="flex items-center gap-2 justify-center mb-8">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <span className="font-bold text-xl">MedicalRAG</span>
          </div>

          <h1 className="text-2xl font-bold text-center mb-2">Create account</h1>
          <p className="text-muted-foreground text-center text-sm mb-8">Join the medical AI platform</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1.5 block">Username</label>
                <input {...register('username')} placeholder="johndoe"
                  className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                {errors.username && <p className="text-destructive text-xs mt-1">{errors.username.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium mb-1.5 block">Full Name</label>
                <input {...register('full_name')} placeholder="John Doe"
                  className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
                {errors.full_name && <p className="text-destructive text-xs mt-1">{errors.full_name.message}</p>}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Email</label>
              <input {...register('email')} type="email" placeholder="doctor@hospital.com"
                className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
              {errors.email && <p className="text-destructive text-xs mt-1">{errors.email.message}</p>}
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Password</label>
              <div className="relative">
                <input {...register('password')} type={showPwd ? 'text' : 'password'} placeholder="••••••••"
                  className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary pr-10" />
                <button type="button" onClick={() => setShowPwd(!showPwd)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password && (
                <div className="mt-2 grid grid-cols-2 gap-1">
                  {checks.map((c) => (
                    <div key={c.label} className={`flex items-center gap-1 text-xs ${c.ok ? 'text-green-600' : 'text-muted-foreground'}`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${c.ok ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                      {c.label}
                    </div>
                  ))}
                </div>
              )}
              {errors.password && <p className="text-destructive text-xs mt-1">{errors.password.message}</p>}
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Confirm Password</label>
              <input {...register('confirm_password')} type="password" placeholder="••••••••"
                className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary" />
              {errors.confirm_password && <p className="text-destructive text-xs mt-1">{errors.confirm_password.message}</p>}
            </div>

            <button type="submit" disabled={isLoading}
              className="w-full bg-primary text-white font-semibold py-2.5 rounded-lg hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-60">
              {isLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            Already have an account?{' '}
            <Link href="/auth/login" className="text-primary font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
