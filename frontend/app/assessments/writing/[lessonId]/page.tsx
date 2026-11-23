"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ProtectedPage } from "@/components/auth-provider";
import { assessments, MAX_WRITING_CHARACTERS, type WritingSubmission, type WritingTask } from "@/lib/assessments";

export default function WritingPage() {
  return <ProtectedPage><WritingPractice /></ProtectedPage>;
}

function WritingPractice() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const router = useRouter();
  const submissionId = useSearchParams().get("submission");
  const [task, setTask] = useState<WritingTask | null>(null);
  const [saved, setSaved] = useState<WritingSubmission | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestKey = useRef<string | null>(null);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    const load = submissionId ? assessments.writing(submissionId).then(row => {
      if (active) { setSaved(row); setTask({ lesson_id: row.lesson_id, title: "Saved writing practice", level: row.level,
        content_version: row.content_version, prompt: row.prompt, draft_preview: row.draft_preview }); }
    }) : assessments.writingTask(lessonId).then(value => { if (active) setTask(value); });
    load.catch(() => { if (active) setError("Writing practice could not load. Return to assessments and retry."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [lessonId, submissionId]);

  async function submit() {
    if (!task || lock.current || !text.trim()) return;
    lock.current = true; setBusy(true); setError("");
    requestKey.current ??= crypto.randomUUID();
    try {
      const submission = await assessments.submitWriting(task.lesson_id, text, requestKey.current);
      setSaved(submission);
      router.replace(`/assessments/writing/${task.lesson_id}?submission=${submission.id}`);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Submission could not be saved. Please retry."); }
    finally { lock.current = false; setBusy(false); }
  }
  async function feedback() {
    if (!saved || lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try { setSaved(await assessments.writingFeedback(saved.id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Feedback is unavailable. Your writing is saved."); }
    finally { lock.current = false; setBusy(false); }
  }

  return <main className="mx-auto max-w-3xl space-y-5 px-5 py-8">
    <Link className="text-violet-700 underline" href="/assessments">Back to assessments</Link>
    <h1 className="text-3xl font-bold">French writing practice</h1>
    <p>Save your original response. Optional AI feedback offers suggestions about task completion, grammar, vocabulary and clarity. It provides no official CEFR or correctness score.</p>
    {loading && <p role="status">Loading writing task…</p>}
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {task && <>
      <section aria-labelledby="writing-task" className="rounded-2xl border border-violet-100 bg-white p-5">
        <h2 id="writing-task" className="font-semibold">{task.title} · {task.level}</h2>
        {task.draft_preview && <p className="my-3 text-amber-800">Authorized draft preview. Independent review is pending.</p>}
        <p className="mt-3 whitespace-pre-wrap">{task.prompt}</p>
      </section>
      {!saved ? <form onSubmit={event => { event.preventDefault(); void submit(); }} className="space-y-3">
        <label htmlFor="writing-response" className="block font-semibold">Your French response</label>
        <textarea id="writing-response" lang="fr" className="min-h-44 w-full rounded-xl border border-slate-300 p-3" maxLength={MAX_WRITING_CHARACTERS}
          value={text} onChange={event => { setText(event.target.value); requestKey.current = null; }} disabled={busy} />
        <p className="text-sm text-slate-600">{text.length} / {MAX_WRITING_CHARACTERS} characters. Avoid personal contact details.</p>
        <button className="button button-primary" disabled={busy || !text.trim()}>{busy ? "Saving…" : "Save writing"}</button>
      </form> : <section aria-labelledby="saved-writing" className="space-y-4 rounded-2xl border border-violet-100 bg-white p-5">
        <h2 id="saved-writing" className="text-xl font-semibold">Your saved original response</h2>
        <p lang="fr" className="whitespace-pre-wrap break-words">{saved.original_text}</p>
        {saved.feedback_status === "unavailable" && <p role="status">AI feedback is unavailable. Your original writing is saved. You can retry.</p>}
        {saved.advisory_feedback ? <section aria-labelledby="advisory-feedback" className="space-y-3">
          <h3 id="advisory-feedback" className="font-semibold">Advisory AI feedback</h3>
          <p>Task completion · {saved.advisory_feedback.task_completion}</p>
          <h4 className="font-semibold">Possible grammar improvements</h4>
          <ul>{saved.advisory_feedback.grammar_suggestions.map((item, index) => <li key={index}>{item}</li>)}</ul>
          <h4 className="font-semibold">Vocabulary suggestions</h4>
          <ul>{saved.advisory_feedback.vocabulary_suggestions.map((item, index) => <li key={index}>{item}</li>)}</ul>
          <p>Clarity · {saved.advisory_feedback.clarity}</p>
        </section> : <button className="button button-secondary" disabled={busy} onClick={() => void feedback()}>{busy ? "Requesting feedback…" : "Request optional AI feedback"}</button>}
        <button className="button button-secondary" disabled={busy} onClick={() => {
          setText(saved.original_text); setSaved(null); requestKey.current = null;
        }}>Write a revision as a new submission</button>
      </section>}
    </>}
  </main>;
}
