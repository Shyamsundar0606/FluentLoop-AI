"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ProtectedPage } from "@/components/auth-provider";
import { LearningTabs } from "@/components/learning-tabs";
import { WritingHistory } from "@/components/writing-history";
import { assessments, type AssessmentDefinition, type AssessmentHistoryItem } from "@/lib/assessments";

export default function AssessmentsPage() {
  return <ProtectedPage><AssessmentLibrary /></ProtectedPage>;
}

function AssessmentLibrary() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<Awaited<ReturnType<typeof assessments.catalog>> | null>(null);
  const [history, setHistory] = useState<AssessmentHistoryItem[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    Promise.all([assessments.catalog(), assessments.history()]).then(([items, page]) => {
      if (active) { setCatalog(items); setHistory(page.items); setNextOffset(page.next_offset); }
    }).catch(() => { if (active) setError("Assessments could not load. Refresh to retry."); });
    return () => { active = false; };
  }, []);

  async function start(item: AssessmentDefinition) {
    if (lock.current) return;
    if (item.skill === "writing") { router.push(`/assessments/writing/${item.lesson_id}`); return; }
    lock.current = true; setBusy(true); setError("");
    try {
      const session = await assessments.start(item);
      router.push(`/learning/sessions/${session.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Assessment unavailable.");
    } finally { lock.current = false; setBusy(false); }
  }

  async function more() {
    if (nextOffset === null || lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const page = await assessments.history(nextOffset);
      setHistory(items => [...items, ...page.items]); setNextOffset(page.next_offset);
    } catch { setError("History could not load. Please retry."); }
    finally { lock.current = false; setBusy(false); }
  }

  return <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
    <LearningTabs />
    <h1 className="text-3xl font-bold">Skills assessments</h1>
    <p>Grammar, vocabulary, reading, listening and writing practice at your saved learning level. Availability depends on authorized content.</p>
    <p className="text-sm text-slate-600">Practice results describe these activities. They do not certify CEFR proficiency. Writing feedback is optional and advisory.</p>
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {!catalog && !error && <p role="status">Loading assessments…</p>}
    {catalog && <section aria-label="Available assessments" className="space-y-4">
      <p>Saved learning level {catalog.level}. <Link className="text-violet-700 underline" href="/settings">Change learning preferences</Link></p>
      {!catalog.items.length && <p>No authorized assessments are available at this level yet.</p>}
      {catalog.items.map(item => <article key={item.id} className="rounded-2xl border border-violet-100 bg-white p-5">
        <p className="capitalize text-violet-700">{item.skill} · {item.level}</p>
        <h2 className="my-2 text-xl font-semibold">{item.title}</h2>
        {!!item.objectives?.length && <ul className="my-2 list-disc pl-5">{item.objectives.map(objective => <li key={objective.title}>{objective.title}</li>)}</ul>}
        <p>{item.skill === "writing" ? "One original response · Optional advisory feedback" : `${item.question_count} questions`} · Allow about {item.duration_minutes} minutes</p>
        {catalog.draft_preview && <p className="my-2 text-amber-800">Authorized draft preview. Independent content review is pending.</p>}
        <button className="button button-primary mt-3" disabled={busy} onClick={() => void start(item)}>Start or resume {item.skill} assessment</button>
      </article>)}
    </section>}
    <section aria-labelledby="assessment-history" className="space-y-3">
      <h2 id="assessment-history" className="text-xl font-semibold">Assessment history</h2>
      {catalog && !history.length && <p>No assessment history yet.</p>}
      <ul className="space-y-3">{history.map(item => <li key={item.id} className="rounded-xl border border-violet-100 bg-white p-4">
        <p>{item.title} · {item.skill} · {item.level}</p>
        <p>{new Date(item.started_at).toLocaleDateString()} · {item.status.replaceAll("_", " ")}</p>
        {item.draft_preview && <p className="text-amber-800">Draft preview</p>}
        <Link className="text-violet-700 underline" href={item.status === "completed" ? `/learning/results/${item.id}` : `/learning/sessions/${item.id}`}>
          {item.status === "completed" ? `View results · ${item.score_points} / ${item.max_score_points}` : `Open saved assessment · ${item.answered} / ${item.question_count} answered`}
        </Link>
      </li>)}</ul>
      {nextOffset !== null && <button className="button button-secondary" disabled={busy} onClick={() => void more()}>Load older assessments</button>}
    </section>
    <WritingHistory />
    <Link className="text-violet-700 underline" href="/progress">View learning progress</Link>
  </main>;
}
