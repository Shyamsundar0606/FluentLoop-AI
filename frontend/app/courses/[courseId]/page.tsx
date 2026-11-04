"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import {
  getCourse,
  listLessons,
  listUnits,
  type Course,
  type Lesson,
  type Unit,
} from "@/lib/curriculum";

export default function CourseDetailsPage() {
  return (
    <ProtectedPage>
      <CourseDetails />
    </ProtectedPage>
  );
}

function CourseDetails() {
  const params = useParams<{ courseId: string }>();
  const courseId = params.courseId;
  const [loaded, setLoaded] = useState<{
    id: string;
    course: Course | null;
    units: Unit[];
    lessons: Record<string, Lesson[]>;
    error?: string;
  } | null>(null);
  const current = loaded?.id === courseId ? loaded : null;
  const course = current?.course ?? null;
  const units = current?.units ?? [];
  const lessons = current?.lessons ?? {};
  const loading = current === null;
  const error = current?.error ?? "";

  useEffect(() => {
    let active = true;
    Promise.all([getCourse(courseId), listUnits(courseId)])
      .then(async ([courseResult, unitsResult]) => {
        const lessonResults = await Promise.all(
          unitsResult.items.map(
            async (unit) => [unit.id, await listLessons(unit.id)] as const,
          ),
        );
        if (!active) return;
        setLoaded({
          id: courseId,
          course: courseResult,
          units: unitsResult.items,
          lessons: Object.fromEntries(
            lessonResults.map(([unitId, result]) => [unitId, result.items]),
          ),
        });
      })
      .catch((reason: unknown) => {
        if (active) {
          setLoaded({
            id: courseId,
            course: null,
            units: [],
            lessons: {},
            error:
              reason instanceof ApiError
                ? reason.message
                : "Course details could not be loaded.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [courseId]);

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
            Loading course…
          </p>
        ) : error ? (
          <p
            role="alert"
            className="mt-6 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
          >
            {error}
          </p>
        ) : course ? (
          <>
            <section className="panel mt-5">
              <p className="eyebrow">{course.level}</p>
              <h1 className="mt-3 text-3xl font-bold">{course.title}</h1>
              {course.draft_preview && (
                <p className="mt-3 inline-flex rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900 dark:bg-amber-950 dark:text-amber-100">
                  Draft Preview · unreviewed content
                </p>
              )}
              <p className="mt-4 max-w-3xl leading-7 muted">
                {course.description}
              </p>
              <p className="mt-5 text-sm muted">
                {course.lesson_count} lessons · {course.unit_count} units ·{" "}
                {course.estimated_minutes} minutes
              </p>
            </section>
            {course.objectives.length > 0 && (
              <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h2 className="text-xl font-semibold">Learning objectives</h2>
                <ul className="mt-3 grid gap-3 sm:grid-cols-2">
                  {course.objectives.map((objective) => (
                    <li
                      key={objective.code}
                      className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-violet-700 dark:text-violet-300">
                        {objective.skill_category}
                      </p>
                      <p className="mt-1 font-medium">{objective.title}</p>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                        {objective.description}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <section className="mt-8 space-y-5" aria-label="Course units">
              {units.map((unit) => (
                <article
                  key={unit.id}
                  className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold uppercase text-slate-500">
                        Unit {unit.sequence_order}
                      </p>
                      <h2 className="mt-1 text-xl font-semibold">
                        {unit.title}
                      </h2>
                    </div>
                    <span className="text-sm text-slate-500">
                      {unit.lesson_count} lessons
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                    {unit.description}
                  </p>
                  <ol className="mt-5 divide-y divide-slate-200 dark:divide-slate-800">
                    {(lessons[unit.id] ?? []).map((lesson) => (
                      <li
                        key={lesson.id}
                        className="flex flex-wrap items-center justify-between gap-3 py-4"
                      >
                        <div>
                          <h3 className="font-medium">{lesson.title}</h3>
                          <p className="mt-1 text-sm text-slate-500">
                            {lesson.estimated_minutes} minutes · {lesson.level}
                          </p>
                          {lesson.draft_preview && (
                            <span
                              data-testid="draft-lesson-label"
                              className="mt-2 inline-flex rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
                            >
                              Draft Preview · unreviewed
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Link
                            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                            href={`/lessons/${lesson.id}`}
                          >
                            Study guide
                          </Link>
                          <Link
                            className="rounded-lg bg-violet-700 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-800 dark:bg-violet-500 dark:text-slate-950"
                            href={`/learn/${lesson.id}`}
                          >
                            Start lesson
                          </Link>
                        </div>
                      </li>
                    ))}
                    {unit.lesson_count === 0 && (
                      <li className="py-4 text-sm text-slate-500">
                        No published lessons in this unit yet.
                      </li>
                    )}
                  </ol>
                </article>
              ))}
              {units.length === 0 && (
                <p className="rounded-xl bg-white p-5 dark:bg-slate-900">
                  No published units are available in this course yet.
                </p>
              )}
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}
