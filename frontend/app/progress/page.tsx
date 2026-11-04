"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/auth-provider";
import { ReviewMetrics } from "@/components/vocabulary-review";
import { ApiError } from "@/lib/api";
import { getLearningProgress, type LessonProgress } from "@/lib/learning";

export default function ProgressPage() {
  return (
    <ProtectedPage>
      <ProgressContent />
    </ProtectedPage>
  );
}

function ProgressContent() {
  const [items, setItems] = useState<LessonProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getLearningProgress()
      .then((result) => {
        if (active) setItems(result.items);
      })
      .catch((reason: unknown) => {
        if (active)
          setError(
            reason instanceof ApiError
              ? reason.message
              : "Learning progress could not be loaded.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const completed = items.filter((item) => item.status === "completed");
  const inProgress = items.filter((item) => item.status === "in_progress");
  const average = completed.length
    ? Math.round(
        completed.reduce((sum, item) => sum + item.latest_score, 0) /
          completed.length,
      )
    : 0;

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-5xl">
        <h1 className="mt-4 text-3xl font-bold">Your learning progress</h1>
        <ReviewMetrics />
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Progress is saved to your account and stays with each lesson when you
          change levels.
        </p>
        {error && (
          <p
            role="alert"
            className="mt-5 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
          >
            {error}
          </p>
        )}
        {loading ? (
          <p role="status" className="mt-8">
            Loading progress…
          </p>
        ) : (
          <>
            <section className="mt-7 grid gap-4 sm:grid-cols-3">
              <Metric
                title="Lessons started"
                value={items.filter((item) => item.first_started_at).length}
              />
              <Metric title="Lessons completed" value={completed.length} />
              <Metric title="Average latest score" value={`${average}%`} />
            </section>
            <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
              <h2 className="text-xl font-bold">Learning history</h2>
              {items.length === 0 ? (
                <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">
                  No lesson progress yet. Start a published lesson from your
                  course library.
                </p>
              ) : (
                <ul className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
                  {items.map((item) => (
                    <li
                      key={item.lesson_id}
                      className="flex flex-wrap items-center justify-between gap-4 py-4"
                    >
                      <div>
                        <p className="font-semibold">{item.lesson_title}</p>
                        <p className="mt-1 text-sm text-slate-500">
                          {item.cefr_level} · {item.status.replace("_", " ")} ·{" "}
                          {item.completion_count} completions
                        </p>
                        {item.last_studied_at && (
                          <p className="mt-1 text-xs text-slate-500">
                            Last studied{" "}
                            {new Date(item.last_studied_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                      <div className="text-right text-sm">
                        {item.status === "completed" ? (
                          <>
                            <p>Best {item.best_score}%</p>
                            <p className="text-slate-500">
                              Latest {item.latest_score}%
                            </p>
                          </>
                        ) : (
                          <Link
                            href={`/learn/${item.lesson_id}`}
                            className="font-semibold text-violet-700 dark:text-violet-300"
                          >
                            Continue lesson
                          </Link>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {inProgress.length > 0 && (
                <p className="mt-3 text-xs text-slate-500">
                  Active lessons can be resumed from the dashboard.
                </p>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: string | number }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </article>
  );
}
