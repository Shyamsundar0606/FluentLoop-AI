"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, getApiErrorMessage } from "@/lib/api";

type ExportPage = { section: string; items: unknown[]; next_offset: number | null; notice: string };

export function AccountPrivacy() {
  const router = useRouter();
  const [sections, setSections] = useState<string[]>([]);
  const [section, setSection] = useState("");
  const [offset, setOffset] = useState(0);
  const [next, setNext] = useState<number | null>(null);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    apiRequest<{ sections: string[] }>("/users/me/data-export").then(data => {
      if (!Array.isArray(data.sections)) throw new Error("Invalid export options.");
      if (active) { setSections(data.sections); setSection(data.sections[0] ?? ""); }
    }).catch(() => { if (active) setError("Export options could not load. Refresh to retry."); });
    return () => { active = false; };
  }, []);
  async function act(action: "export" | "delete") {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(""); setMessage("");
    try {
      if (action === "delete") {
        await apiRequest("/users/me/delete-account", { method: "POST", body: JSON.stringify({ password, confirmation }) });
        router.replace("/login");
      } else {
        const data = await apiRequest<ExportPage>("/users/me/data-export", {
          method: "POST", body: JSON.stringify({ password, section, offset }),
        });
        const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
        const link = document.createElement("a");
        link.href = url; link.download = `fluentloop-${section}-${offset}.json`; link.click();
        URL.revokeObjectURL(url);
        setNext(data.next_offset);
        setMessage(`Downloaded ${data.items.length} records. ${data.next_offset === null ? "This section has no further pages." : "More records are available on the next page."} ${data.notice}`);
      }
    } catch (reason) { setError(getApiErrorMessage(reason, "Privacy request failed. Your request can be retried.")); }
    finally { setPassword(""); lock.current = false; setBusy(false); }
  }
  return <section aria-labelledby="account-privacy-heading" className="mt-6 rounded-3xl border border-slate-200 bg-white p-7 dark:border-slate-800 dark:bg-slate-900">
    <h2 id="account-privacy-heading" className="text-xl font-bold">Export or permanently delete your data</h2>
    <p className="mt-3 text-sm">Confirm your current password for each request. Export downloads one section and page at a time,
      with up to 100 records per page. Files contain private information; store them securely.</p>
    <label htmlFor="privacy-password" className="mt-4 block font-medium">Confirm current password</label>
    <input id="privacy-password" type="password" autoComplete="current-password" maxLength={128}
      className="mt-1 w-full rounded-lg border p-3" value={password} disabled={busy} onChange={event => setPassword(event.target.value)} />
    <form onSubmit={event => { event.preventDefault(); void act("export"); }} className="mt-5 space-y-3">
      <label htmlFor="export-section" className="block font-medium">Data section</label>
      <select id="export-section" className="w-full rounded-lg border p-3" value={section} disabled={busy} onChange={event => {
        setSection(event.target.value); setOffset(0); setNext(null); setMessage("");
      }}>{sections.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select>
      <button className="button button-secondary" disabled={busy || !section || !password}>Download data page</button>
      {next !== null && <button type="button" className="button button-secondary ml-2" disabled={busy} onClick={() => {
        setOffset(next); setNext(null); setMessage("Next page selected. Confirm your password and download it.");
      }}>Select next page</button>}
    </form>
    <details className="mt-6">
      <summary className="font-semibold text-rose-700">Permanently delete account</summary>
      <p className="my-3 text-sm">This permanently removes your account, sessions, learning records, writing and conversations.
        Private audio is queued for deletion and retried if storage is unavailable. This cannot be undone here.
        Independently authored curriculum and restricted review/audit records remain. Operator-managed backups expire
        under the operator retention policy and are not erased immediately. A restricted account reference is retained
        for 90 days after cleanup completes to reconcile backups. Deactivation below retains learning data.</p>
      <form className="space-y-3" onSubmit={event => { event.preventDefault(); void act("delete"); }}>
        <label htmlFor="delete-confirmation" className="block font-medium">Type DELETE MY ACCOUNT to confirm</label>
        <input id="delete-confirmation" autoComplete="off" className="w-full rounded-lg border p-3" value={confirmation}
          disabled={busy} onChange={event => setConfirmation(event.target.value)} />
        <button className="button button-secondary text-rose-700" disabled={busy || !password || confirmation !== "DELETE MY ACCOUNT"}>Permanently delete my account</button>
      </form>
    </details>
    {error && <p className="mt-3" role="alert">{error}</p>}
    {message && <p className="mt-3" role="status">{message}</p>}
  </section>;
}
