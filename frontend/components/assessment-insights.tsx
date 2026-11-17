"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { assessments, type AssessmentInsights } from "@/lib/assessments";

export function AssessmentEvidence() {
  const [data, setData] = useState<AssessmentInsights | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    assessments.insights().then(result => { if (active) setData(result); })
      .catch(() => { if (active) setError("Assessment evidence could not load. Refresh to retry."); });
    return () => { active = false; };
  }, []);
  return <section aria-labelledby="assessment-evidence" className="my-6 rounded-2xl border border-violet-100 bg-white p-5">
    <h2 id="assessment-evidence" className="text-xl font-semibold">Assessment evidence</h2>
    {error ? <p role="alert">{error}</p> : !data ? <p role="status">Loading assessment evidence…</p> : <>
      <p className="my-2">Selected learning level {data.level}. Based on up to {data.sample_limit} recent assessments.</p>
      <ul className="space-y-3">{data.skills.map(skill => <li key={skill.skill}>
        <h3 className="font-semibold capitalize">{skill.skill}</h3>
        <p>{skill.answered_questions ? `${skill.correct_answers} / ${skill.answered_questions} correct across ${skill.completed_sessions} completed sessions` : "Insufficient evidence"}</p>
      </li>)}</ul>
      {data.has_older_history && <p className="mt-2">Older assessments are available in history.</p>}
      {data.writing && <p className="mt-3">Writing · {data.writing.submissions} saved submissions in the latest {data.writing.sample_limit} writing activities. {data.writing.evidence}</p>}
      {!!data.recommendations?.length && <section className="mt-4">
        <h3 className="font-semibold">Review recommendations</h3>
        <p className="text-sm text-slate-600">Unresolved questions from the latest {data.mistake_attempt_window} exercise attempts.</p>
        <ul className="mt-2 space-y-2">{data.recommendations.map(item => <li key={item.url + item.title}>
          <Link href={item.url} className="text-violet-700 underline">{item.title}</Link> · {item.unresolved_questions} unresolved questions
        </li>)}</ul>
      </section>}
      <p className="my-3 text-sm text-slate-600">{data.notice}</p>
    </>}
    <Link className="text-violet-700 underline" href="/assessments">Open assessments and history</Link>
  </section>;
}
