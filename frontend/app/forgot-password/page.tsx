'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthShell, buttonClass, FormMessage, inputClass } from '@/components/auth-shell';
import { apiRequest } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiRequest('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) });
      setSent(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request could not be completed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Reset your password" description="We’ll send a time-limited reset link if an account matches that email.">
      {sent ? <FormMessage>If an account exists for this email, reset instructions have been sent. Check the local inbox at http://localhost:8025.</FormMessage> : (
        <form className="space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium">Email<input className={inputClass} required type="email" autoComplete="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          {error && <FormMessage error>{error}</FormMessage>}
          <button className={buttonClass} disabled={loading}>{loading ? 'Sending…' : 'Send reset link'}</button>
        </form>
      )}
      <p className="mt-5 text-center text-sm text-slate-600 dark:text-slate-300"><Link className="font-semibold text-violet-700 dark:text-violet-300" href="/login">Return to sign in</Link></p>
    </AuthShell>
  );
}
