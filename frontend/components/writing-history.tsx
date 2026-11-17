"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { assessments, type WritingSubmission } from "@/lib/assessments";

export function WritingHistory() {
  const [items, setItems] = useState<WritingSubmission[]>([]);
  const [next, setNext] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    assessments.writingHistory().then(page => {
      if (active) { setItems(page.items); setNext(page.next_offset); }
    }).catch(() => { if (active) setError("Writing history could not load. Refresh to retry."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function more() {
    if (lock.current || next === null) return;
    lock.current = true; setLoading(true); setError("");
    try {
      const page = await assessments.writingHistory(next);
      setItems(current => [...current, ...page.items]); setNext(page.next_offset);
    } catch { setError("Writing history could not load. Please retry."); }
    finally { lock.current = false; setLoading(false); }
  }
  return <section aria-labelledby="writing-history" className="space-y-3">
    <h2 id="writing-history" className="text-xl font-semibold">Writing history</h2>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Loading writing history…</p>}
    {!loading && !error && !items.length && <p>No writing submissions yet.</p>}
    <ul className="space-y-3">{items.map(item => <li key={item.id} className="rounded-xl border border-violet-100 bg-white p-4">
      <p>{item.level} · {new Date(item.created_at).toLocaleDateString()} · {item.draft_preview ? "Draft preview" : "Writing practice"}</p>
      <Link className="text-violet-700 underline" href={`/assessments/writing/${item.lesson_id}?submission=${item.id}`}>Open saved writing and feedback</Link>
    </li>)}</ul>
    {next !== null && <button className="button button-secondary" disabled={loading} onClick={() => void more()}>Load older writing</button>}
  </section>;
}
