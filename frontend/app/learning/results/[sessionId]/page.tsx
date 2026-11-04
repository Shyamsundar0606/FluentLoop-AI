'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ProtectedPage } from '@/components/auth-provider';
import { ApiError } from '@/lib/api';
import {
  getLearningResults,
  getLearningSession,
  type CompletionResult,
  type LearningSession,
} from '@/lib/learning';

export default function LearningResultsPage() {
  return <ProtectedPage><ResultsContent /></ProtectedPage>;
}

function ResultsContent() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [results, setResults] = useState<CompletionResult | null>(null);
  const [session, setSession] = useState<LearningSession | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([getLearningResults(sessionId), getLearningSession(sessionId)])
      .then(([result, savedSession]) => {
        if (active) {
          setResults(result);
          setSession(savedSession);
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof ApiError ? reason.message : 'Your lesson results could not be loaded.');
      });
    return () => { active = false; };
  }, [sessionId]);

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-3xl">
        <Link href="/dashboard" className="text-sm font-semibold text-violet-700 dark:text-violet-300">← Dashboard</Link>
        {!results && !error && <p role="status" className="mt-8">Loading saved results…</p>}
        {error && <p role="alert" className="mt-6 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200">{error}</p>}
        {results && session && (
          <>
            <section className="mt-6 rounded-3xl bg-gradient-to-br from-violet-700 to-indigo-700 p-8 text-white">
              <p className="text-sm font-semibold uppercase tracking-widest text-violet-200">{results.cefr_level} lesson complete</p>
              <h1 className="mt-3 text-3xl font-bold">{results.lesson_title}</h1>
              <p className="mt-5 text-5xl font-bold">{results.percentage}%</p>
              <p className="mt-2 text-violet-100">{results.correct_answers} correct · {results.incorrect_answers} incorrect · {results.total_questions} questions</p>
              <p className="mt-3 text-sm text-violet-100">Completion {results.completion_count} · Completed {new Date(results.completed_at).toLocaleString()}</p>
            </section>
            <p className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
              This exercise score records your work on this lesson; it is not a formal measure or certification of French proficiency.
            </p>
            {session.exercises.some((exercise) => exercise.feedback && !exercise.feedback.is_correct) && (
              <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="text-xl font-bold">Review mistakes</h2>
                <ol className="mt-4 space-y-4">
                  {session.exercises.filter((exercise) => exercise.feedback && !exercise.feedback.is_correct).map((exercise) => (
                    <li key={exercise.id} className="border-t border-slate-100 pt-4 first:border-0 first:pt-0 dark:border-slate-800">
                      <p className="font-semibold">{exercise.exercise_order}. {exercise.prompt}</p>
                      <p className="mt-2 text-sm">Correct answer: <strong>{exercise.feedback?.correct_answer}</strong></p>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{exercise.feedback?.explanation}</p>
                    </li>
                  ))}
                </ol>
              </section>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href={`/learn/${results.lesson_id}`} className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white dark:bg-violet-500 dark:text-slate-950">Retake lesson</Link>
              <Link href="/courses" className="rounded-xl border border-violet-300 px-5 py-3 text-sm font-semibold text-violet-800 dark:border-violet-800 dark:text-violet-200">Back to courses</Link>
              <Link href="/progress" className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold dark:border-slate-700">View progress</Link>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
