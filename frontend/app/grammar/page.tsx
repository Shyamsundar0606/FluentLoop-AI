"use client";

import { useEffect, useState } from "react";

import { ProtectedPage, useAuth } from "@/components/auth-provider";
import { inputClass } from "@/components/auth-shell";
import { ApiError } from "@/lib/api";
import { listGrammar, type GrammarTopic } from "@/lib/curriculum";
import {
  FRENCH_LEVELS,
  isFrenchLevel,
  type FrenchLevel,
} from "@/lib/learning-levels";

export default function GrammarPage() {
  return (
    <ProtectedPage>
      <GrammarBrowser />
    </ProtectedPage>
  );
}

function GrammarBrowser() {
  const { user } = useAuth();
  const [browsedLevel, setBrowsedLevel] = useState<FrenchLevel | null>(null);
  const level =
    browsedLevel ??
    (user && isFrenchLevel(user.preferences.current_level)
      ? user.preferences.current_level
      : "a1");
  const [loaded, setLoaded] = useState<{
    level: FrenchLevel;
    topics: GrammarTopic[];
    error?: string;
  } | null>(null);
  const current = loaded?.level === level ? loaded : null;
  const topics = current?.topics ?? [];
  const loading = current === null;
  const error = current?.error ?? "";

  useEffect(() => {
    let active = true;
    listGrammar(level)
      .then((result) => {
        if (active) setLoaded({ level, topics: result.items });
      })
      .catch((reason: unknown) => {
        if (active) {
          setLoaded({
            level,
            topics: [],
            error:
              reason instanceof ApiError
                ? reason.message
                : "Grammar topics could not be loaded.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [level]);

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">French grammar</h1>
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              Browse explanations and examples from published lessons.
            </p>
          </div>
          <label className="text-sm font-medium">
            Level
            <select
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
        </div>
        {error && (
          <p
            role="alert"
            className="mt-5 rounded-xl border border-rose-300 bg-rose-50 p-4 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200"
          >
            {error}
          </p>
        )}
        {loading ? (
          <p className="mt-8" role="status">
            Loading grammar…
          </p>
        ) : topics.length > 0 ? (
          <section className="mt-6 space-y-4">
            {topics.map((topic) => (
              <article
                key={topic.id}
                className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
              >
                <p className="text-xs font-bold uppercase tracking-wider text-violet-700 dark:text-violet-300">
                  {topic.level}
                </p>
                <h2 className="mt-2 text-xl font-semibold">{topic.title}</h2>
                <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {topic.summary}
                </p>
                {topic.rules.map((rule) => (
                  <p key={rule} className="mt-3 text-sm leading-6">
                    {rule}
                  </p>
                ))}
                {topic.examples.map((example) => (
                  <p key={example.french_sentence} className="mt-3 text-sm">
                    <span className="font-medium">
                      {example.french_sentence}
                    </span>
                    <span className="ml-2 text-slate-500">
                      {example.english_translation}
                    </span>
                    {example.explanation && (
                      <span className="mt-1 block text-slate-500">
                        {example.explanation}
                      </span>
                    )}
                  </p>
                ))}
              </article>
            ))}
          </section>
        ) : !loading && !error ? (
          <p className="mt-7 rounded-2xl border border-slate-200 bg-white p-6 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
            No published grammar topics are available at {level.toUpperCase()}{" "}
            yet.
          </p>
        ) : null}
      </div>
    </main>
  );
}
