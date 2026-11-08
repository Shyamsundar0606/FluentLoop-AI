"use client";

import Link from "next/link";
import { LessonLibrary } from "@/components/lesson-library";
import { LearningTabs } from "@/components/learning-tabs";
import { LearningAlternatives } from "@/components/learning-alternatives";
import { useLearningContext } from "@/lib/use-learning-context";
import { useEffect, useState } from "react";

import { ProtectedPage, useAuth } from "@/components/auth-provider";
import { inputClass } from "@/components/auth-shell";
import { EmptyState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  listCourses,
  listLevels,
  type Course,
  type LevelInfo,
} from "@/lib/curriculum";
import {
  FRENCH_LEVELS,
  isFrenchLevel,
  type FrenchLevel,
} from "@/lib/learning-levels";

export default function CoursesPage() {
  return (
    <ProtectedPage>
      <CourseLibrary />
    </ProtectedPage>
  );
}

function CourseLibrary() {
  const { user } = useAuth();
  const {level,setLevel:setBrowsedLevel}=useLearningContext();
  const [levels, setLevels] = useState<LevelInfo[]>([]);
  const [courseState, setCourseState] = useState<{
    level: FrenchLevel;
    courses: Course[];
    error?: string;
  } | null>(null);
  const [levelError, setLevelError] = useState("");
  const courses = courseState?.level === level ? courseState.courses : [];
  const loading = courseState?.level !== level;
  const error = courseState?.level === level ? (courseState.error ?? "") : "";

  useEffect(() => {
    let active = true;
    listLevels()
      .then((result) => {
        if (active) setLevels(result);
      })
      .catch(() => {
        if (active)
          setLevelError(
            "French level information could not be loaded. Please try again.",
          );
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    listCourses(level)
      .then((result) => {
        if (active) setCourseState({ level, courses: result.items });
      })
      .catch((reason: unknown) => {
        if (active) {
          setCourseState({
            level,
            courses: [],
            error:
              reason instanceof ApiError
                ? reason.message
                : "French courses could not be loaded.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [level]);

  const levelInfo = levels.find((item) => item.code.toLowerCase() === level);

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
        <div className="mx-auto max-w-5xl">
        <LearningTabs />
          <Link href="/review" className="button button-quiet mb-4">Review vocabulary</Link>
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="mt-3 text-3xl font-bold">French courses</h1>
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              Browse published lessons at any level without changing your
              account level.
            </p>
          </div>
          <label className="text-sm font-medium">
            Browse level
            <select
              aria-label="Browse French level"
              className={inputClass}
              value={level}
              onChange={(event) => {
                if (isFrenchLevel(event.target.value))
                  setBrowsedLevel(event.target.value);
              }}
            >
              {FRENCH_LEVELS.map((item) => (
                <option key={item} value={item}>
                  {item.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
        </header>
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
          Your saved level is{" "}
          {user?.preferences.current_level.toUpperCase() ?? "A1"}. Browsing
          another level does not update it.
        </p>

        <LessonLibrary level={level.toUpperCase()} />
        {levelError && (
          <p
            role="alert"
            className="mt-5 text-sm text-rose-700 dark:text-rose-300"
          >
            {levelError}
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="mt-6 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
          >
            {error}
          </p>
        )}
        {loading ? (
          <p className="mt-8" role="status">
            Loading courses…
          </p>
        ) : courses.length > 0 ? (
          <section
            aria-label={`${level.toUpperCase()} courses`}
            className="mt-8 grid gap-5 md:grid-cols-2"
          >
            {courses.map((course) => (
              <article
                key={course.id}
                className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
              >
                <p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">
                  {course.level}
                </p>
                <h2 className="mt-2 text-xl font-bold">{course.title}</h2>
                {course.draft_preview && (
                  <p className="mt-2 inline-flex rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
                    Draft Preview · unreviewed
                  </p>
                )}
                <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {course.description}
                </p>
                <p className="mt-4 text-sm text-slate-500">
                  {course.unit_count} units · {course.lesson_count} lessons ·{" "}
                  {course.estimated_minutes} minutes
                </p>
                <Link
                  href={`/courses/${course.id}`}
                  className="mt-5 inline-flex rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white dark:bg-violet-500 dark:text-slate-950"
                >
                  View course
                </Link>
              </article>
            ))}
          </section>
        ) : !loading && !error ? (
          <div className="mt-8">
            <EmptyState
              title={`No published ${level.toUpperCase()} courses yet`}
            >
              {levelInfo?.content_available
                ? "Courses exist at this level, but none are currently available to learners."
                : "Learning content for this level is not available yet. Lessons will appear here after they have been reviewed and published."}
            </EmptyState>
            <LearningAlternatives />
          </div>
        ) : null}
      </div>
    </main>
  );
}
