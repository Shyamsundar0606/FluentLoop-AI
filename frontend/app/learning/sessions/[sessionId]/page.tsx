"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import {
  getLearningSession,
  resumeLearningSession,
  submitLearningAnswer,
  completeLearningSession,
  type AnswerResult,
  type LearningSession,
} from "@/lib/learning";

export default function LearningSessionPage() {
  return (
    <ProtectedPage>
      <SessionContent />
    </ProtectedPage>
  );
}

function SessionContent() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [session, setSession] = useState<LearningSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedOption, setSelectedOption] = useState("");
  const [pendingKey, setPendingKey] = useState("");
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    getLearningSession(sessionId)
      .then(async (loaded) => {
        if (loaded.status === "completed") {
          router.replace(`/learning/results/${loaded.id}`);
          return;
        }
        if (loaded.status !== "in_progress") {
          throw new Error("This learning session is no longer active.");
        }
        const resumed = await resumeLearningSession(loaded.id);
        if (active) {
          setSession(resumed);
          setShowFeedback(resumed.current_exercise_position > 0);
        }
      })
      .catch((reason: unknown) => {
        if (active)
          setError(
            reason instanceof ApiError
              ? reason.message
              : reason instanceof Error
                ? reason.message
                : "The saved session could not be loaded.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router, sessionId]);

  const currentExercise = useMemo(
    () => session?.exercises[session.current_exercise_position] ?? null,
    [session],
  );
  const lastAnswered = useMemo(
    () => session?.exercises.filter((item) => item.answered).at(-1) ?? null,
    [session],
  );
  async function submitAnswer() {
    if (!session || !currentExercise || !selectedOption) return;
    setSubmitting(true);
    setError("");
    const key = pendingKey || crypto.randomUUID();
    if (!pendingKey) setPendingKey(key);
    try {
      const result = await submitLearningAnswer(
        session.id,
        currentExercise.id,
        selectedOption,
        key,
      );
      const refreshed = await getLearningSession(session.id);
      setSession(refreshed);
      setAnswerResult(result);
      setShowFeedback(true);
      setPendingKey("");
      setSelectedOption("");
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Your answer could not be saved. You can retry safely.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function finishLesson() {
    if (!session) return;
    setSubmitting(true);
    setError("");
    try {
      await completeLearningSession(session.id);
      router.push(`/learning/results/${session.id}`);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "The lesson could not be completed.",
      );
      setSubmitting(false);
    }
  }

  function continueToNext() {
    setShowFeedback(false);
    setAnswerResult(null);
    setError("");
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-24 text-center" role="status">
        Restoring your saved lesson…
      </main>
    );
  }
  if (error && !session) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p
          role="alert"
          className="rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
        >
          {error}
        </p>
        <Link
          href="/dashboard"
          className="mt-5 inline-block font-semibold text-violet-700 dark:text-violet-300"
        >
          Return to dashboard
        </Link>
      </main>
    );
  }
  if (!session) return null;

  const completedQuestions = session.answered_exercises;
  const progressPercent = Math.round(
    (completedQuestions / session.total_exercises) * 100,
  );
  const questionForFeedback = answerResult
    ? (lastAnswered ?? currentExercise)
    : lastAnswered;
  const feedback = answerResult
    ? {
        is_correct: answerResult.is_correct,
        correct_answer: answerResult.correct_answer,
        explanation: answerResult.explanation,
      }
    : questionForFeedback?.feedback;

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-violet-700 dark:text-violet-300"
            >
              ← Save and exit
            </Link>
            <p className="level-badge mt-3">{session.cefr_level}</p>
            <details>
              <summary>Lesson information</summary>
              <p className="text-xs muted">
                Lesson version: {session.lesson_content_version}
              </p>
            </details>
            <h1 className="mt-1 text-3xl font-bold">{session.lesson.title}</h1>
          </div>
          <span className="rounded-full bg-slate-200 px-3 py-1 text-sm font-semibold dark:bg-slate-800">
            {completedQuestions} / {session.total_exercises} answered
          </span>
        </header>

        {session.preview_mode && (
          <aside
            className="mt-5 rounded-xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
            role="status"
          >
            <strong>Draft Preview:</strong> this content is unreviewed and is
            available only for authorized development testing.
          </aside>
        )}

        <div
          className="mt-5 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
          aria-label="Exercise progress"
        >
          <div
            className="h-full bg-violet-600 transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <section className="mt-6 grid gap-5 md:grid-cols-2">
          <article className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-lg font-semibold">Lesson notes</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {session.lesson.description}
            </p>
            {session.lesson.sections.map((section) => (
              <div
                key={`${section.sequence_order}-${section.type}`}
                className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800"
              >
                <h3 className="font-semibold">{section.title}</h3>
                <p className="mt-1 whitespace-pre-line text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {section.content}
                </p>
              </div>
            ))}
          </article>
          <div className="space-y-5">
            {session.lesson.vocabulary.length > 0 && (
              <article className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="text-lg font-semibold">Vocabulary</h2>
                <ul className="mt-3 space-y-3">
                  {session.lesson.vocabulary.map((word) => (
                    <li
                      key={`${word.lemma}-${word.part_of_speech}`}
                      className="border-t border-slate-100 pt-3 first:border-0 first:pt-0 dark:border-slate-800"
                    >
                      <p className="font-semibold">
                        {word.lemma}{" "}
                        <span className="font-normal text-slate-500">
                          — {word.translation}
                        </span>
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {word.grammatical_gender
                          ? `${word.grammatical_gender} · `
                          : ""}
                        {word.part_of_speech}
                        {word.ipa ? ` · ${word.ipa}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              </article>
            )}
            {session.lesson.grammar.map((topic) => (
              <article
                key={topic.title}
                className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
              >
                <h2 className="text-lg font-semibold">{topic.title}</h2>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  {topic.summary}
                </p>
                {topic.rules.map((rule, index) => (
                  <div key={`${topic.title}-${index}`} className="mt-3 text-sm">
                    <p>{rule.explanation}</p>
                    {rule.examples.map((example) => (
                      <p key={example.french} className="mt-2">
                        <strong>{example.french}</strong>
                        <span className="ml-2 text-slate-500">
                          {example.english}
                        </span>
                      </p>
                    ))}
                  </div>
                ))}
              </article>
            ))}
            {session.lesson.dialogues.map((dialogue) => (
              <article
                key={dialogue.title}
                className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
              >
                <h2 className="text-lg font-semibold">{dialogue.title}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {dialogue.context}
                </p>
                <ol className="mt-3 space-y-3 text-sm">
                  {dialogue.turns.map((turn, index) => (
                    <li key={`${index}-${turn.speaker}`}>
                      <strong>
                        {turn.speaker}: {turn.french}
                      </strong>
                      <span className="block text-slate-500">
                        {turn.english}
                      </span>
                    </li>
                  ))}
                </ol>
              </article>
            ))}
          </div>
        </section>

        <section
          className="mt-7 rounded-2xl border border-violet-200 bg-white p-6 dark:border-violet-900 dark:bg-slate-900"
          aria-label="Exercise"
        >
          {showFeedback && feedback && questionForFeedback ? (
            <div>
              <h2
                className={`text-xl font-bold ${feedback.is_correct ? "text-emerald-700 dark:text-emerald-300" : "text-rose-700 dark:text-rose-300"}`}
              >
                {feedback.is_correct ? "Correct!" : "Not quite."}
              </h2>
              <p className="mt-2 text-sm">
                Correct answer: <strong>{feedback.correct_answer}</strong>
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {feedback.explanation}
              </p>
              <p className="mt-3 text-sm text-slate-500">
                Saved score: {session.score_points} / {session.max_score_points}{" "}
                points.
              </p>
              <button
                type="button"
                onClick={continueToNext}
                className="mt-5 rounded-xl bg-violet-700 px-5 py-3 font-semibold text-white dark:bg-violet-500 dark:text-slate-950"
              >
                {session.current_exercise_position >= session.total_exercises
                  ? "Continue to completion"
                  : "Continue"}
              </button>
            </div>
          ) : currentExercise ? (
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">
                Question {currentExercise.exercise_order} of{" "}
                {session.total_exercises}
              </p>
              <h2 className="mt-2 text-xl font-bold">
                {currentExercise.prompt}
              </h2>
              <p className="mt-2 text-sm text-slate-500">
                {currentExercise.instructions}
              </p>
              <fieldset className="mt-5 space-y-3" disabled={submitting}>
                <legend className="sr-only">Choose an answer</legend>
                {currentExercise.options.map((option) => (
                  <label
                    key={option.id}
                    className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 ${selectedOption === option.id ? "border-violet-500 bg-violet-50 dark:bg-violet-950" : "border-slate-200 dark:border-slate-700"}`}
                  >
                    <input
                      type="radio"
                      name="answer"
                      value={option.id}
                      checked={selectedOption === option.id}
                      onChange={() => setSelectedOption(option.id)}
                    />
                    <span>{option.text}</span>
                  </label>
                ))}
              </fieldset>
              {error && (
                <p
                  className="mt-4 text-sm text-rose-700 dark:text-rose-300"
                  role="alert"
                >
                  {error}
                </p>
              )}
              <button
                type="button"
                onClick={() => void submitAnswer()}
                disabled={!selectedOption || submitting}
                className="mt-5 rounded-xl bg-violet-700 px-5 py-3 font-semibold text-white disabled:opacity-50 dark:bg-violet-500 dark:text-slate-950"
              >
                {submitting ? "Saving answer…" : "Submit answer"}
              </button>
            </div>
          ) : (
            <div>
              <h2 className="text-xl font-bold">All questions answered</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Your final result is calculated and saved by the server.
              </p>
              {error && (
                <p
                  className="mt-4 text-sm text-rose-700 dark:text-rose-300"
                  role="alert"
                >
                  {error}
                </p>
              )}
              <button
                type="button"
                onClick={() => void finishLesson()}
                disabled={submitting}
                className="mt-5 rounded-xl bg-violet-700 px-5 py-3 font-semibold text-white disabled:opacity-50 dark:bg-violet-500 dark:text-slate-950"
              >
                {submitting ? "Completing…" : "Complete lesson"}
              </button>
            </div>
          )}
        </section>

        {session.exercises.some((exercise) => exercise.answered) && (
          <details className="mt-5 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <summary className="cursor-pointer font-semibold">
              Saved answer feedback
            </summary>
            <ol className="mt-4 space-y-3">
              {session.exercises
                .filter((exercise) => exercise.answered)
                .map((exercise) => (
                  <li key={exercise.id} className="text-sm">
                    <p className="font-medium">
                      {exercise.exercise_order}. {exercise.prompt}
                    </p>
                    <p
                      className={
                        exercise.feedback?.is_correct
                          ? "text-emerald-700 dark:text-emerald-300"
                          : "text-rose-700 dark:text-rose-300"
                      }
                    >
                      {exercise.feedback?.is_correct ? "Correct" : "Not quite"}{" "}
                      · Correct answer: {exercise.feedback?.correct_answer}
                    </p>
                    <p className="text-slate-500">
                      {exercise.feedback?.explanation}
                    </p>
                  </li>
                ))}
            </ol>
          </details>
        )}
      </div>
    </main>
  );
}
