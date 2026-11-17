"use client";

import { useRef, useState } from "react";
import { apiRequest, getApiErrorMessage } from "@/lib/api";

export type EditableLesson = {
  slug: string; title: string; description: string; estimated_minutes: number;
  sections: { id: string; title: string; body_content: string }[];
  exercises: { id: string; type: string; prompt: string; instructions: string; feedback: string;
    data: Record<string, unknown>; options: { id: string; option_text: string; is_correct: boolean }[] }[];
  id?: string; prerequisites?: string[];
};
export type EditableCourse = {
  title: string; description: string; estimated_minutes: number; level: string;
  source_license: string; attribution: string; source_url: string | null;
  resources?: { kind: string; id: string; editable: boolean; values: Record<string, string | null> }[];
};

export function StructuredDraftEditor({ slug, digest, lessons, course, onEdited }: {
  slug: string; digest: string; lessons: EditableLesson[]; course: EditableCourse; onEdited: () => void;
}) {
  const targets: { id: string; label: string; route: string; value: Record<string, unknown> }[] = lessons.flatMap(lesson => [
    { id: lesson.slug, label: `${lesson.title} · lesson details`, route: "lessons", value: {
      lesson_slug: lesson.slug, title: lesson.title, description: lesson.description, estimated_minutes: lesson.estimated_minutes,
      prerequisites: lesson.prerequisites ?? [],
    } },
    ...lesson.exercises.map(exercise => ({ id: exercise.id, label: `${lesson.title} · ${exercise.prompt}`, route: "exercises", value: {
      exercise_id: exercise.id, prompt: exercise.prompt, instructions: exercise.instructions,
      explanation: exercise.feedback, data: exercise.data, options: exercise.options,
    } })),
  ]);
  targets.push({ id: "course", label: "Course metadata and provenance", route: "course", value: {
    title: course.title, description: course.description, estimated_minutes: course.estimated_minutes, level: course.level,
    source_license: course.source_license, attribution: course.attribution, source_url: course.source_url,
  } });
  for (const resource of course.resources ?? []) {
    if (resource.editable) targets.push({ id: `${resource.kind}:${resource.id}`, label: `${resource.kind} · ${Object.values(resource.values).find(Boolean) ?? resource.id}`,
      route: "resources", value: { kind: resource.kind, resource_id: resource.id, values: resource.values } });
  }
  const [targetId, setTargetId] = useState(targets[0]?.id ?? "");
  const [text, setText] = useState(JSON.stringify(targets[0]?.value ?? {}, null, 2));
  const [version, setVersion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  async function save() {
    const target = targets.find(row => row.id === targetId);
    if (!target || lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const fields: unknown = JSON.parse(text);
      if (!fields || Array.isArray(fields) || typeof fields !== "object") throw new Error("Enter a content object.");
      await apiRequest(`/content-review/${encodeURIComponent(slug)}/${target.route}`, {
        method: "POST", body: JSON.stringify({ ...fields, expected_digest: digest, next_version: version }),
      });
      onEdited();
    } catch (reason) { setError(getApiErrorMessage(reason, "Structured draft could not be saved.")); }
    finally { lock.current = false; setBusy(false); }
  }
  return <details>
    <summary className="font-semibold">Edit lesson details or exercise definition</summary>
    <p className="my-3 text-sm">Edit the selected draft fields. Keep identifiers and exercise format unchanged.
      Answer keys and listening text are staff-only. Saving preserves the prior packet and requires new independent reviews.</p>
    <p className="my-3 text-sm">Shared resources are read-only here. Reclassification requires a separate draft release.
      Prerequisites use the IDs of earlier lessons in this course.</p>
    <details><summary>Lesson identifiers for prerequisites</summary><ul className="text-sm">
      {lessons.map(lesson => <li key={lesson.slug}>{lesson.title}: <code>{lesson.id ?? "Unavailable"}</code></li>)}
    </ul></details>
    <form className="space-y-3" onSubmit={event => { event.preventDefault(); void save(); }}>
      <div>
        <label className="block" htmlFor="structured-draft-item">Draft item</label>
        <select id="structured-draft-item" className="mt-1 w-full rounded-lg border p-2" value={targetId} disabled={busy} onChange={event => {
          setTargetId(event.target.value); setText(JSON.stringify(targets.find(row => row.id === event.target.value)?.value ?? {}, null, 2));
        }}>{targets.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select>
      </div>
      <label className="block" htmlFor="structured-draft-fields">Selected draft fields</label>
      <textarea id="structured-draft-fields" className="min-h-60 w-full rounded-lg border p-3 font-mono text-sm"
        maxLength={100000} value={text} disabled={busy} onChange={event => setText(event.target.value)} />
      <label className="block">Structured content version
        <input className="ml-2 rounded-lg border p-2" required maxLength={32} pattern="[0-9]+\.[0-9]+\.[0-9]+"
          placeholder="0.1.1" value={version} disabled={busy} onChange={event => setVersion(event.target.value)} />
      </label>
      <button className="button button-primary" disabled={busy || !version || !text.trim()}>Save structured draft revision</button>
      {error && <p role="alert">{error}</p>}
    </form>
  </details>;
}
