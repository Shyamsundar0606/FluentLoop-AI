"use client";

import { FormEvent, useEffect, useState } from "react";

import { ProtectedPage, useAuth } from "@/components/auth-provider";
import { inputClass } from "@/components/auth-shell";
import { ApiError } from "@/lib/api";
import { searchVocabulary, type VocabularyItem } from "@/lib/curriculum";
import {
  FRENCH_LEVELS,
  isFrenchLevel,
  type FrenchLevel,
} from "@/lib/learning-levels";

export default function VocabularyPage() {
  return (
    <ProtectedPage>
      <VocabularyBrowser />
    </ProtectedPage>
  );
}

function VocabularyBrowser() {
  const { user } = useAuth();
  const [browsedLevel, setBrowsedLevel] = useState<FrenchLevel | null>(null);
  const level =
    browsedLevel ??
    (user && isFrenchLevel(user.preferences.current_level)
      ? user.preferences.current_level
      : "a1");
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const key = `${level}|${submittedQuery}`;
  const [loaded, setLoaded] = useState<{
    key: string;
    items: VocabularyItem[];
    error?: string;
  } | null>(null);
  const current = loaded?.key === key ? loaded : null;
  const items = current?.items ?? [];
  const loading = current === null;
  const error = current?.error ?? "";

  useEffect(() => {
    let active = true;
    searchVocabulary(level, submittedQuery)
      .then((result) => {
        if (active) setLoaded({ key, items: result.items });
      })
      .catch((reason: unknown) => {
        if (active) {
          setLoaded({
            key,
            items: [],
            error:
              reason instanceof ApiError
                ? reason.message
                : "Vocabulary could not be loaded.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [key, level, submittedQuery]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmittedQuery(query.trim());
  }

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-900 dark:bg-slate-950 dark:text-white sm:px-8">
      <div className="mx-auto max-w-5xl">
        <h1 className="mt-3 text-3xl font-bold">French vocabulary</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Search published vocabulary and examples from the learning database.
        </p>
        <form
          onSubmit={submitSearch}
          className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-[1fr_auto_auto] sm:items-end dark:border-slate-800 dark:bg-slate-900"
        >
          <label className="text-sm font-medium">
            French word
            <input
              className={inputClass}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              maxLength={80}
              placeholder="e.g. bonjour"
            />
          </label>
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
          <button
            type="submit"
            className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white dark:bg-violet-500 dark:text-slate-950"
          >
            Search
          </button>
        </form>
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
            Searching vocabulary…
          </p>
        ) : items.length > 0 ? (
          <ul className="mt-6 grid gap-4 sm:grid-cols-2">
            {items.map((item) => (
              <li
                key={item.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-xl font-semibold">{item.lemma}</h2>
                  <span className="text-sm text-slate-500">
                    {item.translation}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  {item.grammatical_gender
                    ? `${item.grammatical_gender} · `
                    : ""}
                  {item.part_of_speech}
                  {item.ipa ? ` · ${item.ipa}` : ""}
                </p>
                {item.examples.map((example) => (
                  <p key={example.french_text} className="mt-3 text-sm">
                    <span className="font-medium">{example.french_text}</span>
                    <span className="block text-slate-500">
                      {example.english_translation}
                    </span>
                  </p>
                ))}
              </li>
            ))}
          </ul>
        ) : !loading && !error ? (
          <p className="mt-7 rounded-2xl border border-slate-200 bg-white p-6 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
            No published vocabulary matches this search at {level.toUpperCase()}{" "}
            yet.
          </p>
        ) : null}
      </div>
    </main>
  );
}
