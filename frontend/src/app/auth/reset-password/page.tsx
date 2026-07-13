'use client';
import { Suspense } from 'react';
import { useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { Activity, Loader2, CheckCircle, ArrowLeft } from 'lucide-react';
import { authApi } from '@/lib/api';

const requestSchema = z.object({ email: z.string().email('Invalid email') });
const resetSchema = z.object({
  password: z.string().min(8, 'Min 8 chars'),
  confirm: z.string(),
}).refine((d) => d.password === d.confirm, { message: 'Passwords do not match', path: ['confirm'] });

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-md bg-card rounded-2xl border shadow-sm p-8">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <span className="font-bold text-xl">MedicalRAG</span>
        </div>
        {children}
      </div>
    </div>
  );
}

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [sent, setSent] = useState(false);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const requestForm = useForm({ resolver: zodResolver(requestSchema) });
  const resetForm = useForm({ resolver: zodResolver(resetSchema) });

  const onRequest = async (data: any) => {
    setLoading(true);
    try {
      await authApi.forgotPassword(data.email);
      setSent(true);
    } catch { toast.error('Something went wrong'); }
    finally { setLoading(false); }
  };

  const onReset = async (data: any) => {
    setLoading(true);
    try {
      await authApi.resetPassword({ token, password: data.password });
      setDone(true);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Reset failed');
    } finally { setLoading(false); }
  };

  if (done) return (
    <Card>
      <div className="text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Password Reset!</h2>
        <p className="text-muted-foreground mb-6">Your password has been updated successfully.</p>
        <Link href="/auth/login" className="bg-primary text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-primary/90 transition-colors">Sign In</Link>
      </div>
    </Card>
  );

  if (sent) return (
    <Card>
      <div className="text-center">
        <CheckCircle className="w-16 h-16 text-primary mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Check Your Email</h2>
        <p className="text-muted-foreground mb-6">We've sent a password reset link to your email.</p>
        <Link href="/auth/login" className="flex items-center justify-center gap-2 text-sm text-primary hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to Login
        </Link>
      </div>
    </Card>
  );

  if (token) return (
    <Card>
      <h1 className="text-2xl font-bold text-center mb-2">Set New Password</h1>
      <p className="text-muted-foreground text-center text-sm mb-8">Enter your new password below.</p>
      <form onSubmit={resetForm.handleSubmit(onReset)} className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1.5 block">New Password</label>
          <input {...resetForm.register('password')} type="password" placeholder="••••••••"
            className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          {resetForm.formState.errors.password && <p className="text-destructive text-xs mt-1">{(resetForm.formState.errors.password as any).message}</p>}
        </div>
        <div>
          <label className="text-sm font-medium mb-1.5 block">Confirm Password</label>
          <input {...resetForm.register('confirm')} type="password" placeholder="••••••••"
            className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          {resetForm.formState.errors.confirm && <p className="text-destructive text-xs mt-1">{(resetForm.formState.errors.confirm as any).message}</p>}
        </div>
        <button type="submit" disabled={loading} className="w-full bg-primary text-white font-semibold py-2.5 rounded-lg hover:bg-primary/90 flex items-center justify-center gap-2 disabled:opacity-60">
          {loading ? <><Loader2 className="w-4 h-4 animate-spin" />Resetting...</> : 'Reset Password'}
        </button>
      </form>
    </Card>
  );

  return (
    <Card>
      <h1 className="text-2xl font-bold text-center mb-2">Forgot Password?</h1>
      <p className="text-muted-foreground text-center text-sm mb-8">Enter your email and we'll send you a reset link.</p>
      <form onSubmit={requestForm.handleSubmit(onRequest)} className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1.5 block">Email</label>
          <input {...requestForm.register('email')} type="email" placeholder="doctor@hospital.com"
            className="w-full px-3 py-2.5 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          {requestForm.formState.errors.email && <p className="text-destructive text-xs mt-1">{(requestForm.formState.errors.email as any).message}</p>}
        </div>
        <button type="submit" disabled={loading} className="w-full bg-primary text-white font-semibold py-2.5 rounded-lg hover:bg-primary/90 flex items-center justify-center gap-2 disabled:opacity-60">
          {loading ? <><Loader2 className="w-4 h-4 animate-spin" />Sending...</> : 'Send Reset Link'}
        </button>
      </form>
      <Link href="/auth/login" className="flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground mt-6">
        <ArrowLeft className="w-4 h-4" /> Back to Login
      </Link>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" /></div>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
