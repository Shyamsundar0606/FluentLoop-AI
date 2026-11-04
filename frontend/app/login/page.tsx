'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthShell, buttonClass, FormMessage, inputClass } from '@/components/auth-shell';
import { useAuth } from '@/components/auth-provider';
import { apiRequest, getApiErrorMessage } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiRequest('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
      const user = await refreshUser();
      const next = new URLSearchParams(window.location.search).get('next');
      router.replace(next?.startsWith('/') && !next.startsWith('//') ? next : user?.onboarding_completed ? '/dashboard' : '/onboarding');
    } catch (reason) {
      setError(getApiErrorMessage(reason, 'Sign in failed.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Welcome back" description="Sign in to continue your personal French learning journey.">
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium">Email<input className={inputClass} required type="email" autoComplete="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label className="block text-sm font-medium">Password<input className={inputClass} required type={showPassword ? 'text' : 'password'} autoComplete="current-password" maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={showPassword} onChange={(e) => setShowPassword(e.target.checked)} />Show password</label>
          <Link className="font-semibold text-violet-700 dark:text-violet-300" href="/forgot-password">Forgot password?</Link>
        </div>
        {error && <FormMessage error>{error}</FormMessage>}
        <button className={buttonClass} disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
        <p className="text-center text-sm text-slate-600 dark:text-slate-300">New here? <Link className="font-semibold text-violet-700 dark:text-violet-300" href="/register">Create a free account</Link></p>
        <p className="text-center text-xs text-slate-500">Need to verify your email? <Link href="/verify-email" className="underline">Resend verification</Link></p>
      </form>
    </AuthShell>
  );
}
