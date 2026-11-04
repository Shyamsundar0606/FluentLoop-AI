"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { TutorShell } from "@/components/tutor-shell";
import { FormMessage } from "@/components/auth-shell";
import { ai, Recommendation } from "@/lib/ai";

export default function RecommendationsPage() {
  return (
    <TutorShell>
      <Content />
    </TutorShell>
  );
}
function Content() {
  const [rows, setRows] = useState<Recommendation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    ai.recommendations()
      .then((r) => {
        if (active) setRows(r);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  async function refresh() {
    setBusy(true);
    setError("");
    try {
      setRows(await ai.refreshRecommendations());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recommendations unavailable.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h1 className="text-3xl font-bold">Recommended practice</h1>
      <p className="my-4 text-slate-500">
        Suggestions use your actual exercise activity. They are practice
        guidance, not proficiency assessments.
      </p>
      <button
        className="rounded-xl bg-violet-700 px-5 py-3 font-semibold text-white disabled:opacity-50"
        disabled={busy}
        onClick={() => void refresh()}
      >
        {busy ? "Checking activity…" : "Refresh recommendations"}
      </button>
      {error && <FormMessage error>{error}</FormMessage>}
      <ul className="mt-6 space-y-4">
        {rows.map((r) => (
          <li
            key={r.id}
            className="rounded-2xl border bg-white p-5 dark:bg-slate-900"
          >
            <h2 className="font-bold">
              {r.topic} · {r.cefr_level}
            </h2>
            <p className="my-3 text-sm">{r.reason}</p>
            <Link
              className="font-semibold text-violet-700 dark:text-violet-300"
              href={r.lesson?.url ?? "/ai-tutor"}
            >
              {r.suggested_action}
              {r.lesson?.draft_preview ? " · unreviewed draft" : ""}
            </Link>
          </li>
        ))}
      </ul>
      {rows.length === 0 && (
        <p className="mt-6 text-slate-500">
          No recommendations yet. Refresh to check your recent activity, or
          start with an available lesson.
        </p>
      )}
    </>
  );
}
