"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Preferences,
  ProtectedPage,
  useAuth,
} from "@/components/auth-provider";
import { buttonClass, FormMessage, inputClass } from "@/components/auth-shell";
import { apiRequest } from "@/lib/api";
import { FRENCH_LEVELS } from "@/lib/learning-levels";

type SessionInfo = {
  id: string;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  user_agent: string | null;
  current: boolean;
};

export default function SettingsPage() {
  return (
    <ProtectedPage>
      <SettingsContent />
    </ProtectedPage>
  );
}

function SettingsContent() {
  const { user, signOut, refreshUser } = useAuth();
  const router = useRouter();
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      apiRequest<Preferences>("/users/me/preferences"),
      apiRequest<{ sessions: SessionInfo[] }>("/auth/sessions"),
    ])
      .then(([prefs, sessionData]) => {
        setPreferences(prefs);
        setSessions(sessionData.sessions);
      })
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Settings could not be loaded.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preferences) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiRequest<Preferences>("/users/me/preferences", {
        method: "PATCH",
        body: JSON.stringify(preferences),
      });
      setPreferences(updated);
      await refreshUser();
      setMessage("Preferences saved.");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Preferences could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function logout(allDevices: boolean) {
    setError("");
    try {
      await signOut(allDevices);
      router.replace("/login");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign out failed.");
    }
  }

  async function deactivateAccount() {
    if (
      !window.confirm(
        "Deactivate your account and sign out all devices? You will need administrator support to restore it.",
      )
    )
      return;
    setError("");
    try {
      await apiRequest("/auth/deactivate", { method: "POST" });
      router.replace("/login");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Account deactivation failed.",
      );
    }
  }

  const update = (key: keyof Preferences, value: string | number) =>
    setPreferences((current) =>
      current ? { ...current, [key]: value } : current,
    );

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 dark:bg-slate-950 dark:text-white">
      <div className="mx-auto max-w-3xl">
        <section className="mt-5 rounded-3xl border border-slate-200 bg-white p-7 dark:border-slate-800 dark:bg-slate-900 sm:p-9">
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Manage supported learning preferences and account sessions.
          </p>
          {loading && <p className="mt-6">Loading settings…</p>}
          {!loading && preferences && (
            <form className="mt-7 space-y-4" onSubmit={save}>
              <label className="block text-sm font-medium">
                Explanation language
                <select
                  className={inputClass}
                  value={preferences.explanation_language}
                  onChange={(e) =>
                    update("explanation_language", e.target.value)
                  }
                >
                  <option>English</option>
                </select>
                <span className="mt-1 block text-xs text-slate-500">
                  English is the currently available teaching language.
                </span>
              </label>
              <label className="block text-sm font-medium">
                Target language
                <select
                  className={inputClass}
                  value={preferences.target_language}
                  onChange={(e) => update("target_language", e.target.value)}
                >
                  <option>French</option>
                </select>
              </label>
              <label className="block text-sm font-medium">
                Current French level
                <select
                  className={inputClass}
                  value={preferences.current_level}
                  onChange={(e) => update("current_level", e.target.value)}
                >
                  {FRENCH_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level.toUpperCase()}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-xs text-slate-500">
                  This is a personal preference, not official CEFR
                  certification.
                </span>
              </label>
              <label className="block text-sm font-medium">
                Daily study target
                <select
                  className={inputClass}
                  value={preferences.daily_study_minutes}
                  onChange={(e) =>
                    update("daily_study_minutes", Number(e.target.value))
                  }
                >
                  {[5, 10, 15, 20, 30].map((minutes) => (
                    <option key={minutes} value={minutes}>
                      {minutes} minutes
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium">
                Learning focus
                <select
                  className={inputClass}
                  value={preferences.learning_focus}
                  onChange={(e) => update("learning_focus", e.target.value)}
                >
                  {[
                    "balanced",
                    "speaking",
                    "listening",
                    "reading",
                    "writing",
                  ].map((focus) => (
                    <option key={focus} value={focus}>
                      {focus}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium">
                Theme
                <select
                  className={inputClass}
                  value={preferences.theme}
                  onChange={(e) => update("theme", e.target.value)}
                >
                  {["system", "light", "dark"].map((theme) => (
                    <option key={theme} value={theme}>
                      {theme}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium">
                Audio playback speed:{" "}
                {preferences.audio_playback_speed.toFixed(1)}×
                <input
                  className="mt-3 w-full accent-violet-600"
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={preferences.audio_playback_speed}
                  onChange={(e) =>
                    update("audio_playback_speed", Number(e.target.value))
                  }
                />
              </label>
              {message && <FormMessage>{message}</FormMessage>}
              {error && <FormMessage error>{error}</FormMessage>}
              <button className={buttonClass} disabled={saving}>
                {saving ? "Saving…" : "Save preferences"}
              </button>
            </form>
          )}
        </section>
        <section className="mt-6 rounded-3xl border border-slate-200 bg-white p-7 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-xl font-bold">Account and sessions</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            {user?.email} · {user?.role} ·{" "}
            {user?.email_verified ? "Email verified" : "Email not verified"}
          </p>
          <h3 className="mt-6 font-semibold">Active sessions</h3>
          <ul className="mt-3 space-y-2">
            {sessions.map((session) => (
              <li
                key={session.id}
                className="rounded-xl border border-slate-200 p-3 text-xs dark:border-slate-700"
              >
                <span className="font-semibold">
                  {session.current ? "This session" : "Other session"}
                </span>
                <span className="ml-2 text-slate-500">
                  Last used {new Date(session.last_used_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => void logout(false)}
              className="rounded-xl border border-rose-300 px-4 py-3 text-sm font-semibold text-rose-700 dark:border-rose-900 dark:text-rose-300"
            >
              Sign out this device
            </button>
            <button
              type="button"
              onClick={() => void logout(true)}
              className="rounded-xl bg-rose-700 px-4 py-3 text-sm font-semibold text-white"
            >
              Sign out all devices
            </button>
          </div>
          <button
            type="button"
            onClick={() => void deactivateAccount()}
            className="mt-5 text-sm font-medium text-rose-700 underline dark:text-rose-300"
          >
            Deactivate account
          </button>
        </section>
      </div>
    </main>
  );
}
