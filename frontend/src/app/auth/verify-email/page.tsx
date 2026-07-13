'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@/lib/api';
import { Activity, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useI18n } from '@/i18n/context';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { t } = useI18n();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided.');
      return;
    }

    const verify = async () => {
      try {
        await authApi.verifyEmail(token);
        setStatus('success');
      } catch (err: any) {
        setStatus('error');
        setMessage(err?.response?.data?.detail || 'Verification failed. Token may be invalid or expired.');
      }
    };

    verify();
  }, [searchParams]);

  return (
    <div className="bg-card rounded-2xl border shadow-sm p-8 text-center">
      <div className="flex items-center justify-center mb-6">
        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
          {status === 'loading' && <Loader2 className="w-6 h-6 text-primary animate-spin" />}
          {status === 'success' && <CheckCircle className="w-6 h-6 text-green-500" />}
          {status === 'error' && <XCircle className="w-6 h-6 text-destructive" />}
        </div>
      </div>

      <h1 className="text-2xl font-bold mb-2">
        {status === 'loading' && 'Verifying Email...'}
        {status === 'success' && 'Email Verified!'}
        {status === 'error' && 'Verification Failed'}
      </h1>

      <p className="text-muted-foreground mb-8">
        {status === 'loading' && 'Please wait while we verify your email address.'}
        {status === 'success' && 'Your email has been successfully verified. You can now access your account.'}
        {status === 'error' && message}
      </p>

      {status !== 'loading' && (
        <Link 
          href="/auth/login"
          className="inline-flex bg-primary text-white font-semibold px-8 py-2.5 rounded-lg hover:bg-primary/90 transition-colors"
        >
          {status === 'success' ? 'Continue to Login' : 'Back to Login'}
        </Link>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <span className="font-bold text-xl">MedicalRAG</span>
        </div>
        
        <Suspense fallback={
          <div className="bg-card rounded-2xl border shadow-sm p-8 text-center">
            <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" />
          </div>
        }>
          <VerifyEmailContent />
        </Suspense>
      </div>
    </div>
  );
}
