'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthShell, buttonClass, FormMessage, inputClass } from '@/components/auth-shell';
import { apiRequest } from '@/lib/api';

export default function VerifyEmailPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
      if (token) {
        const result = await apiRequest<{ message: string }>('/auth/verify-email', {
          method: 'POST',
          body: JSON.stringify({ token }),
        });
        window.history.replaceState(null, '', window.location.pathname);
        setMessage(result.message);
      } else {
        const result = await apiRequest<{ message: string }>('/auth/resend-verification', {
          method: 'POST',
          body: JSON.stringify({ email }),
        });
        setMessage(result.message);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Email verification could not be completed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Verify your email" description="Use the verification link in your inbox. Links are single-use and expire.">
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium">If you need another link, enter your email<input className={inputClass} type="email" autoComplete="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        {error && <FormMessage error>{error}</FormMessage>}
        {message && <FormMessage>{message}</FormMessage>}
        <button className={buttonClass} disabled={loading}>{loading ? 'Working…' : 'Verify or resend link'}</button>
        <p className="text-center text-sm text-slate-600 dark:text-slate-300"><Link className="font-semibold text-violet-700 dark:text-violet-300" href="/login">Return to sign in</Link></p>
      </form>
    </AuthShell>
  );
}
