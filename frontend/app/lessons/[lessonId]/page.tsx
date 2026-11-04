"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import {
  getLesson,
  getLessonExercises,
  getLessonGrammar,
  getLessonVocabulary,
  type ExercisePreview,
  type GrammarTopic,
  type LessonDetail,
  type VocabularyItem,
} from "@/lib/curriculum";

export default function LessonPreviewPage() {
  return (
    <ProtectedPage>
      <LessonPreview />
    </ProtectedPage>
  );
}

function LessonPreview() {
  const params = useParams<{ lessonId: string }>();
  const lessonId = params.lessonId;
  const [loaded, setLoaded] = useState<{
    id: string;
    lesson: LessonDetail | null;
    vocabulary: VocabularyItem[];
    grammar: GrammarTopic[];
    exercises: ExercisePreview[];
    error?: string;
  } | null>(null);
  const current = loaded?.id === lessonId ? loaded : null;
  const lesson = current?.lesson ?? null;
  const vocabulary = current?.vocabulary ?? [];
  const grammar = current?.grammar ?? [];
  const exercises = current?.exercises ?? [];
  const loading = current === null;
  const error = current?.error ?? "";

  useEffect(() => {
    let active = true;
    Promise.all([
      getLesson(lessonId),
      getLessonVocabulary(lessonId),
      getLessonGrammar(lessonId),
      getLessonExercises(lessonId),
    ])
      .then(
        ([lessonResult, vocabularyResult, grammarResult, exerciseResult]) => {
          if (!active) return;
          setLoaded({
            id: lessonId,
            lesson: lessonResult,
            vocabulary: vocabularyResult.items,
            grammar: grammarResult.items,
            exercises: exerciseResult.items,
          });
        },
      )
      .catch((reason: unknown) => {
        if (active) {
          setLoaded({
            id: lessonId,
            lesson: null,
            vocabulary: [],
            grammar: [],
            exercises: [],
            error:
              reason instanceof ApiError
                ? reason.message
                : "Lesson preview could not be loaded.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [lessonId]);

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/courses"
          className="text-sm font-semibold text-violet-700 dark:text-violet-300"
        >
          ← Course library
        </Link>
        {loading ? (
          <p className="mt-8" role="status">
            Loading lesson preview…
          </p>
        ) : error ? (
          <p
            role="alert"
            className="mt-6 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
          >
            {error}
          </p>
        ) : lesson ? (
          <>
            <header className="panel mt-5">
              <p className="eyebrow">
                {lesson.level} · {lesson.estimated_minutes} minutes
              </p>
              <h1 className="mt-3 text-3xl font-bold">{lesson.title}</h1>
              {lesson.draft_preview && (
                <p className="mt-3 inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900 dark:bg-amber-950 dark:text-amber-100">
                  Draft Preview · unreviewed content
                </p>
              )}
              <p className="mt-4 max-w-3xl leading-7 muted">
                {lesson.description}
              </p>
              {lesson.draft_preview && (
                <p className="mt-3 text-sm text-amber-800 dark:text-amber-200">
                  This preview is for authorized development testing and is not
                  approved for learners.
                </p>
              )}
            </header>

            {lesson.objectives.length > 0 && (
              <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="text-xl font-semibold">What you will learn</h2>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700 dark:text-slate-200">
                  {lesson.objectives.map((item) => (
                    <li key={item.code}>
                      {item.title}: {item.description}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {lesson.sections.map((section) => (
              <section
                key={`${section.sequence_order}-${section.type}`}
                className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
              >
                <h2 className="text-xl font-semibold">{section.title}</h2>
                <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-700 dark:text-slate-200">
                  {section.content}
                </p>
              </section>
            ))}

            {vocabulary.length > 0 && (
              <section className="mt-6">
                <h2 className="text-2xl font-bold">Vocabulary</h2>
                <ul className="mt-4 grid gap-4 sm:grid-cols-2">
                  {vocabulary.map((word) => (
                    <li
                      key={word.id}
                      className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className="text-lg font-semibold">{word.lemma}</h3>
                        <span className="text-sm text-slate-500">
                          {word.translation}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                        {word.grammatical_gender
                          ? `${word.grammatical_gender} · `
                          : ""}
                        {word.part_of_speech}
                        {word.ipa ? ` · ${word.ipa}` : ""}
                      </p>
                      {word.examples.map((example) => (
                        <p key={example.french_text} className="mt-3 text-sm">
                          <span className="font-medium">
                            {example.french_text}
                          </span>
                          <span className="block text-slate-500">
                            {example.english_translation}
                          </span>
                        </p>
                      ))}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {grammar.length > 0 && (
              <section className="mt-6">
                <h2 className="text-2xl font-bold">Grammar</h2>
                <div className="mt-4 space-y-4">
                  {grammar.map((topic) => (
                    <article
                      key={topic.id}
                      className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
                    >
                      <h3 className="text-lg font-semibold">{topic.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                        {topic.summary}
                      </p>
                      {topic.rules.map((rule) => (
                        <p key={rule} className="mt-3 text-sm">
                          {rule}
                        </p>
                      ))}
                      {topic.examples.map((example) => (
                        <p
                          key={example.french_sentence}
                          className="mt-3 text-sm"
                        >
                          <span className="font-medium">
                            {example.french_sentence}
                          </span>
                          <span className="ml-2 text-slate-500">
                            {example.english_translation}
                          </span>
                        </p>
                      ))}
                    </article>
                  ))}
                </div>
              </section>
            )}

            {lesson.dialogues.length > 0 && (
              <section className="mt-6">
                <h2 className="text-2xl font-bold">Dialogue</h2>
                {lesson.dialogues.map((dialogue) => (
                  <article
                    key={dialogue.id}
                    className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
                  >
                    <h3 className="text-lg font-semibold">{dialogue.title}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {dialogue.english_context}
                    </p>
                    <ol className="mt-4 space-y-3">
                      {dialogue.turns.map((turn) => (
                        <li key={turn.sequence_order} className="text-sm">
                          <span className="font-semibold">
                            {turn.speaker_label}:{" "}
                          </span>
                          {turn.french_text}
                          <span className="block text-slate-500">
                            {turn.english_translation}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </article>
                ))}
              </section>
            )}

            {exercises.length > 0 && (
              <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="text-2xl font-bold">Exercise preview</h2>
                <p className="mt-2 text-sm text-slate-500">
                  This is a preview only. Answer keys are not included.
                </p>
                <ol className="mt-4 space-y-5">
                  {exercises.map((exercise) => (
                    <li key={exercise.id}>
                      <p className="font-medium">
                        {exercise.sequence_order}. {exercise.prompt}
                      </p>
                      <p className="mt-1 text-sm text-slate-500">
                        {exercise.instructions}
                      </p>
                      <ul className="mt-2 list-disc pl-5 text-sm">
                        {exercise.options.map((option) => (
                          <li key={option.id}>{option.text}</li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ol>
              </section>
            )}
            <div className="mt-8">
              <Link
                href={`/learn/${lesson.id}`}
                className="inline-flex rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white dark:bg-violet-500 dark:text-slate-950"
              >
                Start interactive lesson
              </Link>
            </div>
          </>
        ) : null}
      </div>
    </main>
  );
}
