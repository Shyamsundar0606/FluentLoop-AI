'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiRequest } from '@/lib/api';
import Link from 'next/link';
import { useAuth } from '@/components/auth-provider';

export function LessonActions({ lessonId, level }: { lessonId: string; level?: string }) {
  const router = useRouter();
  const {user}=useAuth();
  const mismatched=!!level&&!!user&&level.toLowerCase()!==user.preferences.current_level.toLowerCase();
  const [pending, setPending] = useState('');
  const [error, setError] = useState('');
  async function open(action: 'tutor' | 'speaking') {
    if (pending||mismatched) return;
    setPending(action); setError('');
    try {
      const result = await apiRequest<{ url: string }>(`/learning/lessons/${encodeURIComponent(lessonId)}/${action}`, { method: 'POST' });
      router.push(result.url);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Practice is temporarily unavailable.'); setPending(''); }
  }
  return <div className="mt-5 border-t border-violet-100 pt-4"><p className="mb-3 text-sm text-slate-500">Optional conversation practice</p>
    {mismatched&&<p className="mb-3 text-sm">Conversation practice follows your saved level ({user?.preferences.current_level.toUpperCase()}). To use this {level?.toUpperCase()} lesson as conversation context, <Link className="text-violet-700 underline" href="/settings">update your saved French level</Link>. Browsing lessons does not change it.</p>}
    <div className="flex flex-wrap gap-3"><button type="button" className="btn-secondary" disabled={!!pending||mismatched} onClick={() => void open('tutor')}>{pending === 'tutor' ? 'Opening…' : 'Ask AI Tutor'}</button>
      <button type="button" className="btn-secondary" disabled={!!pending||mismatched} onClick={() => void open('speaking')}>{pending === 'speaking' ? 'Opening…' : 'Practice speaking'}</button></div>
    {error && <p role="alert" className="mt-2 text-rose-700">{error}</p>}
  </div>;
}
