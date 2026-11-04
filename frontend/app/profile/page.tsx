"use client";

import { FormEvent, useEffect, useState } from "react";

import { AuthUser, ProtectedPage, useAuth } from "@/components/auth-provider";
import { buttonClass, FormMessage, inputClass } from "@/components/auth-shell";
import { apiRequest } from "@/lib/api";

type ProfileData = Pick<
  AuthUser,
  | "email"
  | "display_name"
  | "preferred_name"
  | "native_language"
  | "country"
  | "timezone"
  | "learning_goal"
  | "email_verified"
>;

export default function ProfilePage() {
  return (
    <ProtectedPage>
      <ProfileContent />
    </ProtectedPage>
  );
}

function ProfileContent() {
  const { refreshUser } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<ProfileData>("/users/me/profile")
      .then(setProfile)
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Profile could not be loaded.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setMessage("");
    setError("");
    if (!profile.display_name.trim()) {
      setError("Display name is required.");
      setSaving(false);
      return;
    }
    try {
      const updated = await apiRequest<ProfileData>("/users/me/profile", {
        method: "PATCH",
        body: JSON.stringify({
          display_name: profile.display_name.trim(),
          preferred_name: profile.preferred_name || null,
          native_language: profile.native_language,
          country: profile.country || null,
          timezone: profile.timezone,
          learning_goal: profile.learning_goal || null,
        }),
      });
      setProfile({ ...profile, ...updated });
      await refreshUser();
      setMessage("Profile saved.");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Profile could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  const update = (key: keyof ProfileData, value: string) =>
    setProfile((current) => (current ? { ...current, [key]: value } : current));

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 dark:bg-slate-950 dark:text-white">
      <div className="mx-auto max-w-3xl">
        <section className="mt-5 rounded-3xl border border-slate-200 bg-white p-7 dark:border-slate-800 dark:bg-slate-900 sm:p-9">
          <h1 className="text-3xl font-bold">Your profile</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Make this space yours. Your saved name appears in your welcome and
            conversations with your tutor.
          </p>
          {loading && <p className="mt-6">Loading profile…</p>}
          {!loading && profile && (
            <form className="mt-7 space-y-4" onSubmit={submit}>
              <label className="block text-sm font-medium">
                Email (cannot be changed here)
                <input className={inputClass} readOnly value={profile.email} />
              </label>
              <label className="block text-sm font-medium">
                Display name
                <input
                  className={inputClass}
                  required
                  maxLength={80}
                  value={profile.display_name}
                  onChange={(e) => update("display_name", e.target.value)}
                />
              </label>
              <label className="block text-sm font-medium">
                Preferred name (optional)
                <input
                  className={inputClass}
                  maxLength={80}
                  value={profile.preferred_name ?? ""}
                  onChange={(e) => update("preferred_name", e.target.value)}
                />
              </label>
              <label className="block text-sm font-medium">
                Native language
                <input
                  className={inputClass}
                  required
                  maxLength={32}
                  value={profile.native_language}
                  onChange={(e) => update("native_language", e.target.value)}
                />
              </label>
              <label className="block text-sm font-medium">
                Country code (optional)
                <input
                  className={inputClass}
                  maxLength={2}
                  placeholder="FR"
                  value={profile.country ?? ""}
                  onChange={(e) =>
                    update("country", e.target.value.toUpperCase())
                  }
                />
              </label>
              <label className="block text-sm font-medium">
                Timezone
                <input
                  className={inputClass}
                  required
                  maxLength={64}
                  placeholder="Europe/Paris"
                  value={profile.timezone}
                  onChange={(e) => update("timezone", e.target.value)}
                />
              </label>
              <label className="block text-sm font-medium">
                Learning goal
                <input
                  className={inputClass}
                  maxLength={80}
                  value={profile.learning_goal ?? ""}
                  onChange={(e) => update("learning_goal", e.target.value)}
                />
              </label>
              {message && <FormMessage>{message}</FormMessage>}
              {error && <FormMessage error>{error}</FormMessage>}
              <button className={buttonClass} disabled={saving}>
                {saving ? "Saving…" : "Save profile"}
              </button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
