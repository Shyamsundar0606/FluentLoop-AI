'use client';

import Link from 'next/link';
import { LessonActions } from '@/components/lesson-actions';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ProtectedPage } from '@/components/auth-provider';
import { ApiError } from '@/lib/api';
import { getLesson, type LessonDetail } from '@/lib/curriculum';
import { startLearningSession } from '@/lib/learning';

export default function StartLessonPage() {
  return <ProtectedPage><StartLesson /></ProtectedPage>;
}

function StartLesson() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const router = useRouter();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    let active = true;
    getLesson(lessonId)
      .then((result) => { if (active) setLesson(result); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof ApiError ? reason.message : 'Lesson details could not be loaded.');
      });
    return () => { active = false; };
  }, [lessonId]);

  async function beginLesson() {
    setStarting(true);
    setError('');
    try {
      const session = await startLearningSession(lessonId);
      router.push(`/learning/sessions/${session.id}`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'The lesson could not be started.');
      setStarting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-3xl">
        <Link href={lesson?`/courses?level=${lesson.level.toLowerCase()}&lesson=${lessonId}`:'/courses'} className="text-sm font-semibold text-violet-700 dark:text-violet-300">← Course library</Link>
        {!lesson && !error && <p role="status" className="mt-8">Loading lesson…</p>}
        {error && <p role="alert" className="mt-6 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200">{error}</p>}
        {lesson && (
          <section className="mt-6 rounded-3xl border border-slate-200 bg-white p-7 dark:border-slate-800 dark:bg-slate-900 sm:p-9">
            <p className="text-sm font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">{lesson.level} · {lesson.estimated_minutes} minutes</p>
            <h1 className="mt-3 text-3xl font-bold">{lesson.title}</h1>
            <p className="mt-4 leading-7 text-slate-600 dark:text-slate-300">{lesson.description}</p>
            {lesson.draft_preview && (
              <aside className="mt-5 rounded-xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
                <strong>Draft Preview:</strong> this AI-assisted content has not received independent review and is not approved for public learning.
              </aside>
            )}
            <div className="mt-6">
              <h2 className="text-lg font-semibold">This session</h2>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-600 dark:text-slate-300">
                <li>Study saved lesson vocabulary, grammar, and examples.</li>
                <li>Answer the lesson exercises; grading and progress are saved on the server.</li>
                <li>You can leave and resume this session later.</li>
              </ul>
            </div>
            <button
              type="button"
              onClick={() => void beginLesson()}
              disabled={starting}
              className="mt-7 rounded-xl bg-violet-700 px-5 py-3 font-semibold text-white disabled:opacity-60 dark:bg-violet-500 dark:text-slate-950"
            >
              {starting ? 'Starting…' : 'Start or continue lesson'}
            </button>
            <LessonActions lessonId={lessonId} />
          </section>
        )}
      </div>
    </main>
  );
}
