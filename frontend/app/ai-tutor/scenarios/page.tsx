"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TutorShell } from "@/components/tutor-shell";
import { useAuth } from "@/components/auth-provider";
import { FormMessage } from "@/components/auth-shell";
import { ai, Scenario } from "@/lib/ai";

export default function ScenariosPage() {
  return (
    <TutorShell>
      <Content />
    </TutorShell>
  );
}
function Content() {
  const { user } = useAuth();
  const level = user?.preferences.current_level.toUpperCase();
  const router = useRouter();
  const [rows, setRows] = useState<Scenario[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    ai.scenarios()
      .then((r) => {
        if (active) setRows(r);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [level]);
  async function start(s: Scenario) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    try {
      const c = await ai.start(s.id);
      sessionStorage.setItem(
        `tutor-draft-${c.id}`,
        "Please begin the scenario and introduce our roles.",
      );
      router.push(`/ai-tutor/${c.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Practice unavailable.");
      setBusy(false);
      lock.current = false;
    }
  }
  return (
    <>
      <h1 className="text-3xl font-bold">Conversation practice · {level}</h1>
      <p className="my-4 text-slate-500">
        Original practice prompts at your selected level. These are separate
        from reviewed courses. Change your saved level in Settings to practice
        another level.
      </p>
      {error && <FormMessage error>{error}</FormMessage>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {rows.map((s) => (
          <article
            key={s.id}
            className="rounded-2xl border border-slate-200 bg-white p-6 dark:bg-slate-900"
          >
            <h2 className="text-xl font-semibold">{s.title}</h2>
            <p className="mt-3">{s.description}</p>
            <p className="mt-3 text-sm">
              Tutor: {s.tutor_role} · You: {s.learner_role}
            </p>
            <p className="mt-2 text-sm text-slate-500">
              Try: {s.suggested_vocabulary.join(", ")}
            </p>
            <p className="mt-3 text-xs text-slate-500">{s.provenance}</p>
            <button
              disabled={busy}
              onClick={() => void start(s)}
              className="mt-5 rounded-xl bg-violet-700 px-4 py-2 font-semibold text-white disabled:opacity-50"
            >
              Start practice
            </button>
          </article>
        ))}
      </div>
    </>
  );
}
