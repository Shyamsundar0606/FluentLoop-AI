"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { TutorShell } from "@/components/tutor-shell";
import { FormMessage, inputClass } from "@/components/auth-shell";
import { ai, Conversation, tutorModes } from "@/lib/ai";

export default function HistoryPage() {
  return (
    <TutorShell>
      <Content />
    </TutorShell>
  );
}
function Content() {
  const [rows, setRows] = useState<Conversation[]>([]);
  const [mode, setMode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    let active = true;
    ai.conversations(mode, offset)
      .then((r) => {
        if (active) setRows(r);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [mode, offset]);
  async function archive(id: string) {
    setBusy(true);
    try {
      await ai.archive(id);
      setRows(await ai.conversations(mode, offset));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not archive.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <h1 className="text-3xl font-bold">Conversation history</h1>
      <label className="my-5 block">
        Filter by mode
        <select
          className={inputClass}
          value={mode}
          onChange={(e) => {
            setMode(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All modes</option>
          {tutorModes.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </label>
      {error && <FormMessage error>{error}</FormMessage>}
      <ul className="space-y-3">
        {rows.map((c) => (
          <li
            key={c.id}
            className="flex items-center justify-between gap-3 rounded-xl border bg-white p-5 dark:bg-slate-900"
          >
            <div>
              <Link
                className="font-semibold text-violet-700 dark:text-violet-300"
                href={`/ai-tutor/${c.id}`}
              >
                {c.title}
              </Link>
              <p className="mt-2 text-xs text-slate-500">
                {c.cefr_level} · {c.mode} · {c.status} ·{" "}
                {new Date(c.updated_at).toLocaleString()}
              </p>
            </div>
            {c.status === "active" && (
              <button
                disabled={busy}
                onClick={() => void archive(c.id)}
                className="text-sm font-semibold"
              >
                Archive
              </button>
            )}
          </li>
        ))}
      </ul>
      {rows.length === 0 && (
        <p className="mt-4">No conversations on this page.</p>
      )}
      <div className="mt-5 flex gap-4">
        <button
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Previous
        </button>
        <button
          disabled={rows.length < 20}
          onClick={() => setOffset(offset + 20)}
        >
          Next
        </button>
      </div>
    </>
  );
}
