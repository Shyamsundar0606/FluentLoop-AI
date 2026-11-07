'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { ProtectedPage } from '@/components/auth-provider';
import { ExerciseInput, answerReady } from '@/components/exercise-input';
import { LessonReading } from '@/components/lesson-reading';
import { LessonActions } from '@/components/lesson-actions';
import { ApiError } from '@/lib/api';
import { getLearningSession, resumeLearningSession, submitExerciseAnswer, saveLearningPosition,
  completeLearningSession, learningReturnUrl, submittedAnswerText,
  type ExerciseAnswer, type LearningSession } from '@/lib/learning';

export default function LearningSessionPage() { return <ProtectedPage><SessionContent /></ProtectedPage>; }

function SessionContent() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [session, setSession] = useState<LearningSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [answer, setAnswer] = useState<ExerciseAnswer | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const busy = useRef(false);
  const pending = useRef<{ key: string; answer: ExerciseAnswer } | null>(null);
  const focusTarget = useRef<HTMLElement>(null);

  useEffect(() => {
    let active = true;
    getLearningSession(sessionId).then(async loaded => {
      if (loaded.status === 'completed') { router.replace(`/learning/results/${loaded.id}`); return; }
      if (loaded.status !== 'in_progress') throw new Error('This learning session is no longer active.');
      const resumed = await resumeLearningSession(loaded.id);
      if (active) { setSession(resumed); setShowFeedback(resumed.current_exercise_position > 0); }
    }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'The saved session could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [router, sessionId]);

  const guided = session?.lesson.learning_flow_version === 1 && (session.activity_key ?? 'lesson') === 'lesson';
  const stage = guided ? Math.min(session?.current_section_position ?? 0, 3) : 3;
  const currentExercise = session?.exercises[session.current_exercise_position] ?? null;
  const lastAnswered = session?.exercises.filter(item => item.answered).at(-1) ?? null;
  useEffect(() => { focusTarget.current?.focus(); }, [session?.id, stage, currentExercise?.id, showFeedback]);

  async function move(position: number) {
    if (!session || busy.current) return;
    busy.current = true; setSubmitting(true); setError('');
    try { setSession(await saveLearningPosition(session.id, position)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'This step could not be saved. Please retry.'); }
    finally { busy.current = false; setSubmitting(false); }
  }
  async function reloadSaved() {
    if (!session || busy.current) return;
    busy.current = true; setSubmitting(true); setError('');
    try {
      const saved = await getLearningSession(session.id);
      setSession(saved); setShowFeedback(saved.current_exercise_position > 0);
      if (saved.current_exercise_position !== session.current_exercise_position) { setAnswer(null); pending.current = null; }
      setNeedsRefresh(false);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Saved progress could not be loaded. Your answer is still here.'); }
    finally { busy.current = false; setSubmitting(false); }
  }
  async function submitAnswer() {
    if (!session || !currentExercise || !answer || !answerReady(currentExercise, answer) || busy.current) return;
    busy.current = true; setSubmitting(true); setError('');
    const request = pending.current ?? { key: crypto.randomUUID(), answer };
    pending.current = request;
    try {
      await submitExerciseAnswer(session.id, currentExercise.id, request.answer, request.key);
      const saved = await getLearningSession(session.id);
      setSession(saved); setShowFeedback(true); setAnswer(null); pending.current = null; setNeedsRefresh(false);
    } catch (reason) {
      setNeedsRefresh(true);
      setError(reason instanceof ApiError ? reason.message : 'Your answer could not be confirmed. Retry the same answer or reload saved progress.');
    } finally { busy.current = false; setSubmitting(false); }
  }
  async function finish() {
    if (!session || busy.current) return;
    busy.current = true; setSubmitting(true); setError('');
    try { await completeLearningSession(session.id); router.push(`/learning/results/${session.id}`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The activity could not be completed.'); busy.current = false; setSubmitting(false); }
  }

  if (loading) return <main className="mx-auto max-w-3xl px-6 py-20" role="status">Restoring your saved lesson…</main>;
  if (!session) return <main className="mx-auto max-w-3xl px-6 py-12"><p role="alert">{error}</p><Link href="/courses" className="mt-5 inline-block text-violet-700">Return to Learn</Link></main>;
  const feedback = lastAnswered?.feedback;
  const practice = session.activity_key?.startsWith('practice:');
  return <main className="mx-auto max-w-3xl px-5 py-8 text-slate-900">
    <Link href={learningReturnUrl(session)} className="text-sm font-semibold text-violet-700">← Save and exit</Link>
    <header className="mt-5"><p className="level-badge">{session.cefr_level}</p><h1 className="mt-2 text-3xl font-bold">{session.lesson.title}</h1>
      <p className="mt-3 text-sm text-slate-500">{session.answered_exercises} / {session.total_exercises} answered</p>
      {practice && <p className="mt-2 text-sm">Focused practice · does not complete the full lesson</p>}
      <progress aria-label="Exercise progress" className="mt-3 block h-2 w-full accent-violet-600" max={session.total_exercises || 1} value={session.answered_exercises} />
      <details className="mt-3 text-xs text-slate-500"><summary>Lesson information</summary><p>Lesson version: {session.lesson_content_version}</p></details>
    </header>
    {session.preview_mode && <aside role="status" className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><strong>Draft Preview:</strong> unreviewed content for authorized development testing.</aside>}
    {guided && <ol aria-label="Lesson steps" className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500">{['Introduction', 'Explanation', 'Examples', 'Exercises'].map((label, i) => <li key={label} aria-current={stage === i ? 'step' : undefined} className={stage === i ? 'font-semibold text-violet-700' : ''}>{i + 1}. {label}</li>)}</ol>}
    <section ref={focusTarget} tabIndex={-1} aria-label={stage < 3 ? 'Lesson reading' : 'Exercise'} className="mt-6 rounded-2xl border border-violet-100 bg-white p-5 outline-none sm:p-7">
      {stage < 3 ? <><LessonReading lesson={session.lesson} stage={stage} />
        <div className="mt-6 flex flex-wrap gap-3">{stage > 0 && <button type="button" className="button button-secondary" disabled={submitting} onClick={() => void move(stage - 1)}>Back</button>}
          <button type="button" className="button button-primary" disabled={submitting} onClick={() => void move(stage + 1)}>{submitting ? 'Saving step…' : stage === 2 ? 'Start exercises' : 'Continue lesson'}</button></div>
      </> : showFeedback && feedback && lastAnswered ? <>
        <h2 className={`text-2xl font-bold ${feedback.is_correct ? 'text-emerald-700' : 'text-rose-700'}`}>{feedback.is_correct ? 'Correct!' : 'Not quite.'}</h2>
        <p className="mt-4">Your answer: <strong lang="fr">{submittedAnswerText(lastAnswered)}</strong></p>
        <p className="mt-3">Correct answer: <strong>{feedback.correct_answer}</strong></p>
        <p className="mt-3 leading-7 text-slate-600">{feedback.explanation}</p>
        <p className="mt-3 text-sm text-slate-500">Saved score: {session.score_points} / {session.max_score_points} points.</p>
        <button type="button" className="button button-primary mt-6" onClick={() => { setShowFeedback(false); setError(''); }}>{session.current_exercise_position >= session.total_exercises ? 'Continue to completion' : 'Continue'}</button>
      </> : currentExercise ? <>
        <p className="text-sm text-violet-700">Question {currentExercise.exercise_order} of {session.total_exercises}</p>
        <h2 className="mt-2 text-2xl font-bold">{currentExercise.prompt}</h2><p className="mt-3 text-slate-600">{currentExercise.instructions}</p>
        <ExerciseInput key={currentExercise.id} sessionId={session.id} exercise={currentExercise} disabled={submitting || needsRefresh} value={answer}
          onChange={next => { pending.current = null; setAnswer(next); }} />
        <button type="button" className="button button-primary mt-6" disabled={submitting || !answerReady(currentExercise, answer)} onClick={() => void submitAnswer()}>{submitting ? 'Saving answer…' : 'Submit answer'}</button>
      </> : <><h2 className="text-2xl font-bold">All questions answered</h2><p className="mt-3">Your final result is calculated and saved by the server.</p>
        <button type="button" className="button button-primary mt-6" disabled={submitting} onClick={() => void finish()}>{submitting ? 'Completing…' : practice ? 'Complete practice' : 'Complete lesson'}</button></>}
      {error && <p role="alert" className="mt-4 text-rose-700">{error}</p>}
      {needsRefresh && <button type="button" className="button button-secondary mt-3" disabled={submitting} onClick={() => void reloadSaved()}>Reload saved progress</button>}
    </section>
    {stage === 3 && <div className="mt-5 space-y-4">
      {guided && <button type="button" className="text-sm font-semibold text-violet-700" disabled={submitting} onClick={() => void move(1)}>Back to explanation</button>}
      <details className="rounded-xl border border-slate-200 p-4"><summary className="font-semibold">Lesson reference</summary><div className="mt-4"><LessonReading lesson={session.lesson} stage={1} /><div className="mt-5"><LessonReading lesson={session.lesson} stage={2} /></div><LessonActions lessonId={session.lesson_id} /></div></details>
    </div>}
    {session.exercises.some(e => e.answered) && <details className="mt-5 rounded-xl border border-slate-200 p-4"><summary className="font-semibold">Saved answer feedback</summary><ol className="mt-4 space-y-4">{session.exercises.filter(e => e.answered).map(e => <li key={e.id}><p className="font-semibold">{e.exercise_order}. {e.prompt}</p><p className="mt-2">Your answer: {submittedAnswerText(e)}</p><p>Correct answer: {e.feedback?.correct_answer}</p><p className="text-sm text-slate-500">{e.feedback?.explanation}</p></li>)}</ol></details>}
  </main>;
}