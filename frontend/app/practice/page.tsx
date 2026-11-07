'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedPage } from '@/components/auth-provider';
import { LearningTabs } from '@/components/learning-tabs';
import { apiRequest } from '@/lib/api';
import { useLearningContext } from '@/lib/use-learning-context';
import { MistakePractice } from '@/components/mistake-practice';
import { LearningAlternatives } from '@/components/learning-alternatives';

const categories = [
  ['grammar', 'Grammar', 'Use the right form in a short sentence.'],
  ['sentence_building', 'Sentence building', 'Arrange words and remember French word order.'],
  ['listening', 'Listening', 'Listen to French and check the meaning.'],
  ['mistakes', 'Review mistakes', 'Revisit your most recent unresolved exercise errors.'],
];
interface Availability { category: string; available_exercises: number; availability_reason: string }

function availabilityMessage(item: Availability | undefined, level: string) {
  if (!item) return 'Checking availability…';
  if (item.available_exercises > 0) return `${item.available_exercises} authorized exercises available`;
  if (item.availability_reason === 'no_published_content') return `No published exercises are available at ${level} yet. Unpublished fixtures require a separate authorized preview account.`;
  if (item.availability_reason === 'no_unresolved_mistakes') return 'No unresolved mistakes in your available lessons. Answer exercises first; only recorded mistakes appear here.';
  return `No permitted exercises are available for this activity at ${level} yet.`;
}

export default function PracticePage() { return <ProtectedPage><Practice /></ProtectedPage>; }

function Practice() {
  const router = useRouter();
  const context=useLearningContext();
  const level=context.level.toUpperCase();
  const [catalog, setCatalog] = useState<{ level: string; items: Availability[] } | null>(null);
  const [pending, setPending] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    apiRequest<{ items: Availability[] }>(`/learning/practice/catalog?level=${level}`)
      .then(result => { if (active) setCatalog({ level, items: result.items }); })
      .catch(() => { if (active) setError('Practice availability could not be loaded. Please refresh.'); });
    return () => { active = false; };
  }, [level]);

  async function start(category: string) {
    if (pending || catalog?.level !== level || !catalog.items.find(item => item.category === category)?.available_exercises) return;
    setPending(category); setError('');
    try {
      const session = await apiRequest<{ id: string }>('/learning/practice/sessions', {
        method: 'POST', body: JSON.stringify({ category, level }),
      });
      router.push(`/learning/sessions/${session.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Practice unavailable.');
      setPending('');
    }
  }

  return <main className="mx-auto max-w-5xl px-5 py-8">
    <LearningTabs /><p className="text-violet-700">{level}</p>
    <h1 className="mt-2 text-3xl font-bold">A little practice, every day</h1>
    <p className="mt-3 text-slate-600">Choose one skill. Focused practice saves your answers separately from full lesson completion.</p>
    {error && <p role="alert" className="mt-4 text-rose-700">{error}</p>}
    {context.category==='mistakes'?<MistakePractice level={level} lessonId={context.lessonId}/>:<div className="mt-6 grid gap-4 sm:grid-cols-2">
      <article className="rounded-2xl border border-violet-100 p-6">
        <h2 className="text-xl font-semibold">Vocabulary</h2>
        <p className="mt-2 text-slate-600">Review enrolled words with your existing spaced repetition schedule.</p>
        <Link href="/review" className="mt-4 inline-block font-semibold text-violet-700">Review vocabulary →</Link>
      </article>
      {categories.map(([id, title, description]) => {
        const item = catalog?.level === level ? catalog.items.find(entry => entry.category === id) : undefined;
        const unavailable = !item?.available_exercises;
        return <article key={id} className="rounded-2xl border border-violet-100 p-6">
          <h2 className="text-xl font-semibold">{title}</h2>
          <p className="mt-2 text-slate-600">{description}</p>
          <p id={`${id}-availability`} className="mt-3 text-sm text-slate-500">{availabilityMessage(item, level)}</p>
          <button type="button" aria-describedby={`${id}-availability`} disabled={unavailable || !!pending}
            className={`mt-4 rounded-xl border px-5 py-3 font-semibold ${unavailable ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-500' : 'border-violet-700 bg-violet-700 text-white disabled:cursor-wait disabled:opacity-60'}`}
            onClick={() => void start(id)}>{pending === id ? 'Opening…' : 'Start practice'}</button>
        </article>;
      })}
    </div>}
    {context.category!=='mistakes'&&catalog?.level===level&&catalog.items.every(item=>item.available_exercises===0)&&<LearningAlternatives/>}
  </main>;
}
