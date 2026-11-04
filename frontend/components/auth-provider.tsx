"use client";

import {
  createContext,
  Suspense,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";

import { apiRequest } from "@/lib/api";
import type { FrenchLevel } from "@/lib/learning-levels";
import { AppShell } from "./app-shell";

export type Preferences = {
  explanation_language: "English";
  target_language: "French";
  current_level: FrenchLevel;
  target_level: FrenchLevel | null;
  daily_study_minutes: number;
  learning_focus: string;
  theme: "light" | "dark" | "system";
  audio_playback_speed: number;
};

export type AuthUser = {
  id: string;
  email: string;
  role: "learner" | "admin";
  email_verified: boolean;
  display_name: string;
  preferred_name: string | null;
  native_language: string;
  country: string | null;
  timezone: string;
  learning_goal: string | null;
  onboarding_completed: boolean;
  preferences: Preferences;
};

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  refreshUser: () => Promise<AuthUser | null>;
  signOut: (allDevices?: boolean) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const result = await apiRequest<{ user: AuthUser }>("/auth/me");
      setUser(result.user);
      return result.user;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refreshUser(), 0);
    return () => window.clearTimeout(timer);
  }, [refreshUser]);

  const signOut = useCallback(async (allDevices = false) => {
    await apiRequest(allDevices ? "/auth/logout-all" : "/auth/logout", {
      method: "POST",
    });
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, refreshUser, signOut }),
    [user, loading, refreshUser, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}

export function ProtectedPage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-3xl px-6 py-24 text-center text-slate-600 dark:text-slate-300">
          Loading your secure account…
        </main>
      }
    >
      <ProtectedPageContent>{children}</ProtectedPageContent>
    </Suspense>
  );
}

function ProtectedPageContent({ children }: { children: React.ReactNode }) {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-24 text-center text-slate-600 dark:text-slate-300">
        Loading your secure account…
      </main>
    );
  }
  return (
    <AppShell user={user} onSignOut={() => signOut()}>
      {children}
    </AppShell>
  );
}
