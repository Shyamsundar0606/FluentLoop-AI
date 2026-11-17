"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { apiRequest, getApiErrorMessage } from "@/lib/api";
import { StructuredDraftEditor, type EditableLesson, type EditableCourse } from "./structured-draft-editor";

type Revision = { id: string; version: string; digest: string; created_at: string };
type RevisionPage = { items: Revision[]; next_offset: number | null };
type AuthoringPacket = {
  digest: string; can_author: boolean;
  content: EditableCourse & { version: string; lessons: EditableLesson[] };
};

export function DraftImport({ onCreated }: { onCreated: (slug: string) => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  async function create(event: FormEvent) {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const body: unknown = JSON.parse(text);
      const result = await apiRequest<{ slug: string }>("/content-review/drafts", { method: "POST", body: JSON.stringify(body) });
      onCreated(result.slug);
    } catch (reason) { setError(getApiErrorMessage(reason, "Draft creation failed.")); }
    finally { lock.current = false; setBusy(false); }
  }
  return <details className="rounded-xl border border-violet-100 bg-white p-4">
    <summary className="font-semibold">Create an assessment draft release</summary>
    <p className="my-3 text-sm">Paste an authored vocabulary, reading or writing source pack. Existing lexical references are required. Content remains draft and needs independent review.</p>
    <form onSubmit={event => void create(event)} className="space-y-3">
      <label htmlFor="draft-source" className="block font-semibold">Draft source JSON</label>
      <textarea id="draft-source" className="min-h-40 w-full rounded-lg border p-3 font-mono text-sm" value={text}
        maxLength={400000} disabled={busy} onChange={event => setText(event.target.value)} />
      <button className="button button-primary" disabled={busy || !text.trim()}>{busy ? "Validating draft…" : "Create unpublished draft"}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  </details>;
}

export function CurriculumAuthoring({ slug, packet, onEdited }: {
  slug: string; packet: AuthoringPacket; onEdited: () => void;
}) {
  const sections = packet.content.lessons.flatMap(lesson => lesson.sections.map(section => ({ ...section, lesson: lesson.title })));
  const [sectionId, setSectionId] = useState(sections[0]?.id ?? "");
  const [body, setBody] = useState(sections[0]?.body_content ?? "");
  const [version, setVersion] = useState("");
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [comparison, setComparison] = useState<{ changes: unknown[]; total_changes: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const path = `/content-review/${encodeURIComponent(slug)}`;
  useEffect(() => {
    let active = true;
    apiRequest<RevisionPage>(`${path}/revisions`).then(page => {
      if (active) { setRevisions(page.items); setNext(page.next_offset); setBefore(page.items[1]?.id ?? ""); setAfter(page.items[0]?.id ?? ""); }
    }).catch(() => { if (active) setError("Stored versions could not load. Reopen this packet to retry."); });
    return () => { active = false; };
  }, [path]);

  async function act(action: "snapshot" | "edit" | "compare" | "more") {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      if (action === "edit") {
        await apiRequest(`${path}/sections`, { method: "POST", body: JSON.stringify({
          expected_digest: packet.digest, next_version: version, section_id: sectionId, body_content: body,
        }) });
        onEdited();
      } else if (action === "compare") {
        setComparison(await apiRequest(`${path}/compare?before=${encodeURIComponent(before)}&after=${encodeURIComponent(after)}`));
      } else {
        if (action === "snapshot") await apiRequest(`${path}/revisions`, { method: "POST" });
        const page = await apiRequest<RevisionPage>(`${path}/revisions?offset=${action === "more" ? next ?? 0 : 0}`);
        setRevisions(current => action === "more" ? [...current, ...page.items] : page.items);
        setNext(page.next_offset);
        if (action === "snapshot") { setBefore(page.items[1]?.id ?? ""); setAfter(page.items[0]?.id ?? ""); }
      }
    } catch (reason) { setError(getApiErrorMessage(reason, "Authoring operation failed.")); }
    finally { lock.current = false; setBusy(false); }
  }

  return <section aria-labelledby="curriculum-versions" className="space-y-4 rounded-xl border border-violet-100 p-4">
    <h3 id="curriculum-versions" className="text-lg font-semibold">Draft authoring and stored versions</h3>
    {error && <p role="alert">{error}</p>}
    {packet.can_author && <>
      <button className="button button-secondary" disabled={busy} onClick={() => void act("snapshot")}>Save current packet version</button>
      <details><summary className="font-semibold">Edit a draft section</summary>
        <p className="my-3 text-sm">Saving preserves the previous packet, creates a higher content version and requires new independent reviews. Published courses cannot be edited here.</p>
        <form onSubmit={event => { event.preventDefault(); void act("edit"); }} className="space-y-3">
          <label className="block">Section
            <select className="mt-1 w-full rounded-lg border p-2" value={sectionId} disabled={busy} onChange={event => {
              setSectionId(event.target.value); setBody(sections.find(section => section.id === event.target.value)?.body_content ?? "");
            }}>{sections.map(section => <option key={section.id} value={section.id}>{section.lesson} · {section.title}</option>)}</select>
          </label>
          <div>
            <label htmlFor="draft-section-text" className="block">Section text</label>
            <textarea id="draft-section-text" className="mt-1 min-h-40 w-full rounded-lg border p-3" maxLength={4000} value={body} disabled={busy} onChange={event => setBody(event.target.value)} />
          </div>
          <label className="block">New content version
            <input className="ml-2 rounded-lg border p-2" required pattern="[0-9]+\.[0-9]+\.[0-9]+" placeholder="0.1.1" maxLength={32}
              value={version} disabled={busy} onChange={event => setVersion(event.target.value)} />
          </label>
          <button className="button button-primary" disabled={busy || !body.trim() || !version || !sectionId}>Save draft revision</button>
        </form>
      </details>
      <StructuredDraftEditor slug={slug} digest={packet.digest} lessons={packet.content.lessons} course={packet.content} onEdited={onEdited} />
    </>}
    {!revisions.length && <p>No historical packet versions have been saved yet.</p>}
    {!!revisions.length && <>
      <ul className="space-y-2 text-sm">{revisions.map(row => <li key={row.id}>{row.version} · {new Date(row.created_at).toLocaleString()} · <code className="break-all">{row.digest}</code></li>)}</ul>
      {next !== null && <button className="button button-secondary" disabled={busy} onClick={() => void act("more")}>Load older versions</button>}
      <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); void act("compare"); }}>
        <label>Earlier version<select className="ml-2 max-w-full rounded-lg border p-2" value={before} onChange={event => setBefore(event.target.value)} required>
          <option value="">Choose a stored version</option>{revisions.map(row => <option key={row.id} value={row.id}>{row.version} · {row.digest.slice(0, 8)}</option>)}
        </select></label>
        <label>Later version<select className="ml-2 max-w-full rounded-lg border p-2" value={after} onChange={event => setAfter(event.target.value)} required>
          <option value="">Choose a stored version</option>{revisions.map(row => <option key={row.id} value={row.id}>{row.version} · {row.digest.slice(0, 8)}</option>)}
        </select></label>
        <button className="button button-secondary" disabled={busy || !before || !after}>Compare stored versions</button>
      </form>
    </>}
    {comparison && <section aria-label="Stored version changes"><p>{comparison.total_changes} changed fields. Showing up to 1000.</p>
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words text-sm">{JSON.stringify(comparison.changes, null, 2)}</pre>
    </section>}
  </section>;
}
