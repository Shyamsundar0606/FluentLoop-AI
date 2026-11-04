"use client";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { TutorShell } from "@/components/tutor-shell";
import { buttonClass, FormMessage, inputClass } from "@/components/auth-shell";
import { ai, Conversation, tutorModes, TutorMode } from "@/lib/ai";

export default function TutorPage() {
  return (
    <TutorShell>
      <Content />
    </TutorShell>
  );
}
function Content() {
  const { user } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<TutorMode>("tutor");
  const [text, setText] = useState("");
  const [recent, setRecent] = useState<Conversation[]>([]);
  const [status, setStatus] = useState("Checking availability…");
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    ai.health()
      .then((r) => {
        if (active)
          setStatus(
            r.available
              ? "Ready to practice"
              : "Tutor unavailable. Your lessons remain available.",
          );
      })
      .catch(() => {
        if (active)
          setStatus("Tutor unavailable. Regular lessons remain available.");
      });
    ai.conversations()
      .then((r) => {
        if (active) setRecent(r);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  async function start(event: FormEvent) {
    event.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      const c = await ai.create(mode, text.slice(0, 100));
      if (text.trim())
        sessionStorage.setItem(`tutor-draft-${c.id}`, text.trim());
      router.push(`/ai-tutor/${c.id}`);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not create conversation.",
      );
      lock.current = false;
      setBusy(false);
    }
  }
  return (
    <>
      <p className="text-sm font-semibold text-violet-700">
        Your French level · {user?.preferences.current_level.toUpperCase()}
      </p>
      <h1 className="mt-2 text-3xl font-bold">AI French Tutor</h1>
      {user?.display_name && (
        <p className="mt-3 font-medium">
          Welcome, {user.display_name}. Ready to practice French?
        </p>
      )}
      <p className="mt-3 text-slate-500">
        Ask a question, explore a word, or practice a conversation at your saved
        level.
      </p>
      <p role="status" className="my-4 text-sm">
        {status}
      </p>
      <form onSubmit={start} className="panel space-y-4 mt-6">
        <label className="block">
          Practice mode
          <select
            className={inputClass}
            value={mode}
            onChange={(e) => setMode(e.target.value as TutorMode)}
          >
            {tutorModes.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          Your question
          <textarea
            className={inputClass}
            maxLength={4000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What is the difference between être and avoir?"
          />
        </label>
        <button className={buttonClass} disabled={busy}>
          {busy ? "Creating…" : "Start a new conversation"}
        </button>
        {error && <FormMessage error>{error}</FormMessage>}
      </form>
      <div className="my-5 flex flex-wrap gap-2">
        {[
          "How do I introduce myself?",
          "What does pourtant mean?",
          "Explain être and avoir.",
        ].map((q) => (
          <button
            key={q}
            onClick={() => setText(q)}
            className="rounded-full border px-4 py-2 text-sm"
          >
            {q}
          </button>
        ))}
      </div>
      <details className="mt-8">
        <summary>Recent conversations</summary>
        <ul className="mt-4 space-y-3">
          {recent.slice(0, 5).map((c) => (
            <li key={c.id}>
              <Link
                className="text-violet-700 dark:text-violet-300"
                href={`/ai-tutor/${c.id}`}
              >
                {c.title} · {c.cefr_level}
              </Link>
            </li>
          ))}
        </ul>
        {recent.length === 0 && (
          <p className="mt-3 text-sm text-slate-500">
            Your conversations will be saved here.
          </p>
        )}
      </details>
    </>
  );
}
