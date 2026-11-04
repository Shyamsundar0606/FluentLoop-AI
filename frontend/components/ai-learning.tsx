"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ai, Conversation } from "@/lib/ai";

export function AILearning() {
  const [latest, setLatest] = useState<Conversation | null>(null);
  const [status, setStatus] = useState("Checking tutor availability…");
  useEffect(() => {
    let active = true;
    ai.health()
      .then((r) => {
        if (active)
          setStatus(
            r.available
              ? "AI Tutor is ready"
              : "AI Tutor is currently unavailable. Your lessons remain available.",
          );
      })
      .catch(() => {
        if (active) setStatus("Tutor availability could not be checked.");
      });
    ai.conversations()
      .then((rows) => {
        if (active) setLatest(rows.find((c) => c.status === "active") ?? null);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return (
    <section className="mt-6 rounded-2xl border border-violet-200 bg-white p-6 dark:border-violet-900 dark:bg-slate-900">
      <h2 className="text-xl font-bold">AI Learning</h2>
      <p aria-live="polite" className="mt-2 text-sm text-slate-500">
        {status}
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {[
          [
            "/ai-tutor",
            "AI French Tutor",
            "Ask a question or practice French.",
          ],
          [
            latest ? `/ai-tutor/${latest.id}` : "/ai-tutor/history",
            "Continue Conversation",
            latest ? latest.title : "Your saved tutor sessions appear here.",
          ],
          [
            "/ai-tutor/recommendations",
            "Recommended Practice",
            "Review topics based on previous exercises.",
          ],
          [
            "/ai-tutor/scenarios",
            "Conversation Practice",
            "Try a real-life French dialogue.",
          ],
        ].map(([href, title, text]) => (
          <Link
            key={title}
            href={href}
            className="rounded-xl bg-slate-50 p-4 hover:ring-2 hover:ring-violet-400 dark:bg-slate-800"
          >
            <h3 className="font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-slate-500">{text}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
