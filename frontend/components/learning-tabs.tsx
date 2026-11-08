'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiRequest } from '@/lib/api';
import { useLearningContext } from '@/lib/use-learning-context';

export function LearningTabs() {
  const path = usePathname();
  const {level}=useLearningContext();
  const [mode, setMode] = useState<string>('');
  useEffect(() => { let active = true;
    apiRequest<{mode:string}>('/learning/access').then(result => { if(active) setMode(result.mode); }).catch(() => { if(active) setMode('unavailable'); });
    return () => { active = false; };
  }, []);
  return <><nav aria-label="Learn sections" className="mb-6 flex gap-1 border-b border-violet-100 py-3">
    {[['/courses', 'Lessons'], ['/grammar', 'Grammar'], ['/practice', 'Practice']].map(([href, label]) =>
      <Link key={href} href={`${href}?level=${level}`} aria-current={path === href ? 'page' : undefined}
        className={`min-w-0 flex-1 rounded-lg px-3 py-3 text-center font-semibold sm:px-5 ${path === href ? 'bg-violet-100 text-violet-800' : 'text-slate-600 hover:bg-violet-50'}`}>{label}</Link>)}
  </nav>{mode && <aside role="status" aria-label="Learning access" className="mb-6 rounded-xl border border-violet-100 bg-violet-50 p-4 text-sm text-slate-700">
    {mode === 'draft_preview' ? 'Authorized draft preview. Development fixtures are unreviewed and remain unpublished.' : mode === 'published_only' ? 'Published content only for this account. Development fixtures require a separate authorized developer-preview account; signing in as a learner does not enable preview.' : 'Learning access could not be confirmed. Reload this page to retry.'}
  </aside>}</>;
}
