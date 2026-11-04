'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { ProtectedPage, useAuth } from '@/components/auth-provider';
import { FormMessage } from '@/components/auth-shell';
import { apiRequest } from '@/lib/api';
import { FRENCH_LEVELS, isFrenchLevel, type FrenchLevel } from '@/lib/learning-levels';

const goals = ['Daily conversations', 'Living in France', 'French for work', 'French for university', 'French examinations', 'General fluency'] as const;
const targets = [5, 10, 15, 20, 30] as const;

type Answers = { current_level: FrenchLevel; explanation_language: 'English'; learning_goal: string; daily_study_minutes: number };
const initialAnswers: Answers = { current_level: 'a1', explanation_language: 'English', learning_goal: 'Daily conversations', daily_study_minutes: 15 };

export default function OnboardingPage() {
  return <ProtectedPage><OnboardingFlow /></ProtectedPage>;
}

function OnboardingFlow() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>(initialAnswers);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const completed = useRef(false);

  useEffect(() => {
    if (!user) return;
    const key = `fluentloop-onboarding-${user.id}`;
    const saved = window.localStorage.getItem(key);
    const persistedAnswers: Answers = {
      ...initialAnswers,
      current_level: isFrenchLevel(user.preferences.current_level) ? user.preferences.current_level : initialAnswers.current_level,
      learning_goal: user.learning_goal || initialAnswers.learning_goal,
      daily_study_minutes: user.preferences.daily_study_minutes,
      explanation_language: user.preferences.explanation_language,
    };
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as {
          step?: unknown;
          answers?: Partial<Omit<Answers, 'current_level'>> & { current_level?: unknown };
        };
        const restoredAnswers: Answers = {
          ...persistedAnswers,
          ...parsed.answers,
          current_level: isFrenchLevel(parsed.answers?.current_level)
            ? parsed.answers.current_level
            : persistedAnswers.current_level,
        };
        window.setTimeout(() => {
          setAnswers(restoredAnswers);
          if (typeof parsed.step === 'number') setStep(Math.min(Math.max(parsed.step, 0), 5));
          setReady(true);
        }, 0);
        return;
      } catch {
        window.localStorage.removeItem(key);
      }
    }
    window.setTimeout(() => {
      setAnswers(persistedAnswers);
      setReady(true);
    }, 0);
  }, [user]);

  useEffect(() => {
    if (ready && user && !completed.current) {
      window.localStorage.setItem(`fluentloop-onboarding-${user.id}`, JSON.stringify({ step, answers }));
    }
  }, [ready, step, answers, user]);

  async function finish() {
    setError('');
    setLoading(true);
    try {
      await apiRequest('/users/me/onboarding', {
        method: 'POST',
        body: JSON.stringify({ ...answers, current_level: answers.current_level, learning_focus: 'balanced' }),
      });
      completed.current = true;
      if (user) window.localStorage.removeItem(`fluentloop-onboarding-${user.id}`);
      await refreshUser();
      router.replace('/dashboard');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Onboarding could not be saved.');
    } finally {
      setLoading(false);
    }
  }

  const title = ['Welcome', 'Your starting point', 'Explanation language', 'Your learning goal', 'Daily practice', 'Ready to begin'][step];
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900 dark:bg-slate-950 dark:text-white">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between"><Link href="/dashboard" className="font-semibold text-violet-700 dark:text-violet-300">FluentLoop AI</Link><span className="text-sm text-slate-500">Step {step + 1} of 6</span></div>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"><div className="h-full rounded-full bg-violet-600 transition-all" style={{ width: `${((step + 1) / 6) * 100}%` }} /></div>
        <section className="mt-8 rounded-3xl border border-slate-200 bg-white p-7 shadow-lg dark:border-slate-800 dark:bg-slate-900 sm:p-10">
          <h1 className="text-3xl font-bold">{title}</h1>
          {step === 0 && user?.display_name && <p className="mt-4 font-semibold">Hello, {user.display_name}. Your registered name is already saved.</p>}
          {step === 0 && <p className="mt-5 text-lg leading-8 text-slate-600 dark:text-slate-300">FluentLoop AI helps you learn French from zero. You do not need any prior French knowledge. Your answers help personalize your learning preferences and are not an official proficiency assessment.</p>}
          {step === 1 && <fieldset className="mt-6 space-y-3"><legend className="mb-3 text-sm text-slate-600 dark:text-slate-300">Select your current French level.</legend>{FRENCH_LEVELS.map((level) => <label key={level} className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700"><input type="radio" name="level" checked={answers.current_level === level} onChange={() => setAnswers({ ...answers, current_level: level })} />{level.toUpperCase()}</label>)}</fieldset>}
          {step === 2 && <div className="mt-6 space-y-3"><label className="flex items-center gap-3 rounded-xl border border-violet-300 bg-violet-50 p-4 dark:bg-violet-950/30"><input type="radio" checked readOnly />English <span className="ml-auto text-xs font-semibold text-emerald-700">Available</span></label>{['Tamil', 'Hindi', 'More languages'].map((language) => <div key={language} className="flex items-center justify-between rounded-xl border border-slate-200 p-4 text-slate-400 dark:border-slate-700"><span>{language}</span><span className="text-xs">Planned — not selectable yet</span></div>)}</div>}
          {step === 3 && <fieldset className="mt-6 space-y-3"><legend className="sr-only">Choose your learning goal</legend>{goals.map((goal) => <label key={goal} className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700"><input type="radio" name="goal" checked={answers.learning_goal === goal} onChange={() => setAnswers({ ...answers, learning_goal: goal })} />{goal}</label>)}</fieldset>}
          {step === 4 && <fieldset className="mt-6 space-y-3"><legend className="mb-3 text-sm text-slate-600 dark:text-slate-300">Choose a study target you can maintain.</legend>{targets.map((minutes) => <label key={minutes} className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700"><input type="radio" name="minutes" checked={answers.daily_study_minutes === minutes} onChange={() => setAnswers({ ...answers, daily_study_minutes: minutes })} />{minutes} minutes per day</label>)}</fieldset>}
          {step === 5 && <div className="mt-6 space-y-4"><p className="text-slate-600 dark:text-slate-300">We’ll save these settings to your profile:</p><ul className="list-inside list-disc space-y-2"><li>Starting level: {answers.current_level.toUpperCase()}</li><li>Explanation language: English</li><li>Goal: {answers.learning_goal}</li><li>Daily target: {answers.daily_study_minutes} minutes</li></ul></div>}
          {error && <div className="mt-5"><FormMessage error>{error}</FormMessage></div>}
          <div className="mt-8 flex justify-between gap-3"><button type="button" disabled={!ready || step === 0 || loading} onClick={() => setStep(step - 1)} className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold disabled:opacity-40 dark:border-slate-700">Back</button>{step < 5 ? <button type="button" disabled={!ready} onClick={() => setStep(step + 1)} className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60 dark:bg-violet-500 dark:text-slate-950">Continue</button> : <button type="button" onClick={() => void finish()} disabled={!ready || loading} className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60 dark:bg-violet-500 dark:text-slate-950">{loading ? 'Saving…' : 'Save and open dashboard'}</button>}</div>
          {!ready && <p className="mt-3 text-xs text-slate-500">Restoring your saved progress…</p>}
        </section>
      </div>
    </main>
  );
}
