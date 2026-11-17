"use client";

import { useEffect, useRef, useState } from "react";
import { apiRequest, getApiErrorMessage } from "@/lib/api";

type Motivation = {
  enabled: boolean; timezone: string; total_xp: number; today_activities: number;
  current_streak: number; best_streak: number; has_more?: boolean; notice: string;
  achievements: { key: string; title: string; earned_at: string }[];
  xp_policy: Record<string, number>;
};
type RewardPage = { items: { id: string; kind: string; xp: number; study_date: string }[]; next_offset: number | null };

export function LearningMotivation() {
  const [data, setData] = useState<Motivation | null>(null);
  const [history, setHistory] = useState<RewardPage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    apiRequest<Motivation>("/study/motivation").then(value => { if (active) setData(value); })
      .catch(() => { if (active) setError("Learning motivation could not load. Refresh to retry."); });
    return () => { active = false; };
  }, []);
  async function update(action: "sync" | "toggle" | "history") {
    if (!data || lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      if (action === "history") {
        const page = await apiRequest<RewardPage>(`/study/motivation/history?offset=${history?.next_offset ?? 0}`);
        setHistory(current => ({ items: [...(current?.items ?? []), ...page.items], next_offset: page.next_offset }));
      } else if (action === "toggle") {
        await apiRequest("/users/me/preferences", { method: "PATCH", body: JSON.stringify({ motivation_enabled: !data.enabled }) });
        setData(await apiRequest<Motivation>("/study/motivation"));
      } else setData(await apiRequest<Motivation>("/study/motivation/sync", { method: "POST" }));
    } catch (reason) { setError(getApiErrorMessage(reason, "Learning motivation could not update.")); }
    finally { lock.current = false; setBusy(false); }
  }
  return <section aria-labelledby="learning-motivation" className="my-6 space-y-3 rounded-2xl border border-violet-100 bg-white p-5">
    <h2 id="learning-motivation" className="text-xl font-semibold">Learning motivation</h2>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p role="status">Loading saved learning milestones…</p>}
    {data && <>
      {data.enabled ? <>
        <p>{data.total_xp} XP · {data.today_activities} completed activities today</p>
        <p>{data.current_streak} consecutive study days · Best {data.best_streak} days</p>
        <p className="text-sm text-slate-600">Calendar days use the saved activity timezone. Current timezone {data.timezone}. Update rewards to include completed activities.</p>
        <button className="button button-secondary" disabled={busy} onClick={() => void update("sync")}>Update rewards from completed activities</button>
        {data.has_more && <p>More completed history is available. Update again to include the next batch.</p>}
        <details><summary className="font-semibold">Earned achievements</summary>
          {data.achievements.length ? <ul className="mt-2 space-y-2">{data.achievements.map(item => <li key={item.key}>{item.title} · {new Date(item.earned_at).toLocaleDateString()}</li>)}</ul> : <p>No achievements recorded yet.</p>}
        </details>
        <details><summary className="font-semibold">How XP is awarded</summary>
          <ul>{Object.entries(data.xp_policy).map(([kind, xp]) => <li key={kind}>{kind.replaceAll("_", " ")} · {xp} XP per completed activity</li>)}</ul>
          <p className="mt-2 text-sm">Draft previews do not earn XP. {data.notice}</p>
        </details>
        {(!history || history.next_offset !== null) && <button className="button button-secondary" disabled={busy} onClick={() => void update("history")}>{history ? "Load older rewards" : "View reward history"}</button>}
        {history && <ul className="space-y-1 text-sm">{history.items.map(item => <li key={item.id}>{item.study_date} · {item.kind.replaceAll("_", " ")} · {item.xp} XP</li>)}</ul>}
      </> : <p>Motivational features are disabled. Your learning progress remains available in Progress.</p>}
      <button className="text-violet-700 underline" disabled={busy} onClick={() => void update("toggle")}>{data.enabled ? "Disable motivational features" : "Enable motivational features"}</button>
    </>}
  </section>;
}
