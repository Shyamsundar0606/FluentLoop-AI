'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthShell, buttonClass, FormMessage, inputClass } from '@/components/auth-shell';
import { apiRequest } from '@/lib/api';

export default function ResetPasswordPage() {
  const [values, setValues] = useState({ password: '', confirm_password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    if (values.password !== values.confirm_password) {
      setError('Passwords do not match.');
      return;
    }
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
    if (!token) {
      setError('The reset link is missing or invalid. Request a new link.');
      return;
    }

    setLoading(true);
    try {
      await apiRequest('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, ...values }),
      });
      window.history.replaceState(null, '', window.location.pathname);
      setComplete(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Choose a new password" description="Use at least 12 characters with uppercase, lowercase, and a number.">
      {complete ? <div className="space-y-4"><FormMessage>Your password was reset and your existing sessions were signed out.</FormMessage><Link href="/login" className="font-semibold text-violet-700 dark:text-violet-300">Sign in</Link></div> : (
        <form className="space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium">New password<input className={inputClass} required minLength={12} maxLength={128} autoComplete="new-password" type={showPassword ? 'text' : 'password'} value={values.password} onChange={(e) => setValues({ ...values, password: e.target.value })} /></label>
          <label className="block text-sm font-medium">Confirm new password<input className={inputClass} required minLength={12} maxLength={128} autoComplete="new-password" type={showPassword ? 'text' : 'password'} value={values.confirm_password} onChange={(e) => setValues({ ...values, confirm_password: e.target.value })} /></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showPassword} onChange={(e) => setShowPassword(e.target.checked)} />Show passwords</label>
          {error && <FormMessage error>{error}</FormMessage>}
          <button className={buttonClass} disabled={loading}>{loading ? 'Updating…' : 'Reset password'}</button>
        </form>
      )}
    </AuthShell>
  );
}
