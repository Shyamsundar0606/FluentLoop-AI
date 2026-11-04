"use client";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ProtectedPage, useAuth } from "@/components/auth-provider";
import { FormMessage, inputClass } from "@/components/auth-shell";
import { Button, Card, Icon, PageHeader } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { DailyPlanPanel } from "@/components/daily-plan";
import { listCourses } from "@/lib/curriculum";
import { getLearningDashboard, type LearningDashboard } from "@/lib/learning";
import {
  FRENCH_LEVELS,
  isFrenchLevel,
  type FrenchLevel,
} from "@/lib/learning-levels";

export default function DashboardPage() {
  return (
    <ProtectedPage>
      <DashboardContent />
    </ProtectedPage>
  );
}
function DashboardContent() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const userId = user?.id;
  const currentLevel = user?.preferences.current_level;
  const [choice, setChoice] = useState<{
    forLevel: string;
    value: FrenchLevel;
  } | null>(null);
  const selectedLevel =
    choice && choice.forLevel === currentLevel
      ? choice.value
      : currentLevel && isFrenchLevel(currentLevel)
        ? currentLevel
        : "a1";
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [learning, setLearning] = useState<LearningDashboard | null>(null);
  const [learningError, setLearningError] = useState("");
  const [availability, setAvailability] = useState<{
    level: string;
    count: number;
  } | null>(null);
  useEffect(() => {
    if (user && !user.onboarding_completed) router.replace("/onboarding");
  }, [router, user]);
  useEffect(() => {
    if (!userId) return;
    let active = true;
    getLearningDashboard()
      .then((result) => {
        if (active) setLearning(result);
      })
      .catch(() => {
        if (active) setLearningError("Learning progress could not be loaded.");
      });
    listCourses(currentLevel ?? "a1")
      .then((result) => {
        if (active)
          setAvailability({ level: currentLevel ?? "a1", count: result.total });
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [userId, currentLevel]);
  if (!user) return null;
  const active = learning?.active_sessions[0];
  async function saveLevel(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await apiRequest("/users/me/preferences", {
        method: "PATCH",
        body: JSON.stringify({ current_level: selectedLevel }),
      });
      await refreshUser();
      setMessage("French level updated.");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "French level could not be updated.",
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <main>
      <PageHeader
        eyebrow="Make a little time for French"
        title={`Bonjour, ${user.display_name.trim().split(/\s+/)[0] || "Learner"}!`}
        description="Pick up where you left off, or try something new today."
      />
      <DailyPlanPanel />
      <div className="home-grid">
        <Card className="welcome-panel">
          <span className="level-badge">
            {user.preferences.current_level.toUpperCase()} · Your learning path
          </span>
          <h2>
            {active
              ? "Ready for your next step?"
              : "Every journey starts with a little practice."}
          </h2>
          <p>
            {active
              ? `Continue ${active.lesson_title}. Your answers are saved as you go.`
              : "Explore lessons at your level, or start a conversation with your tutor."}
          </p>
          <Link
            href={active ? `/learning/sessions/${active.id}` : "/courses"}
            className="button button-primary mt-6"
          >
            {active ? "Continue lesson" : "Browse courses"}
            <Icon name="arrow" />
          </Link>
          {availability && availability.level === currentLevel && (
            <p className="mt-4 text-xs">
              {availability.count
                ? `${availability.count} ${availability.count === 1 ? "course" : "courses"} available at your level.`
                : "Reviewed lessons will appear in your course library."}
            </p>
          )}
        </Card>
        <Card>
          <p className="eyebrow">Today’s learning goal</p>
          <h2 className="panel-title">A little consistency goes a long way.</h2>
          <p className="goal-number">
            {user.preferences.daily_study_minutes}
            <small> minutes / day</small>
          </p>
          <p className="text-xs muted">
            {user.learning_goal || "Build confidence in everyday French."}
          </p>
          <details className="mt-5 border-t border-slate-100">
            <summary>Learning preferences</summary>
            <form onSubmit={saveLevel} className="space-y-3">
              <label className="block text-xs">
                Change your French level
                <select
                  className={inputClass}
                  value={selectedLevel}
                  onChange={(event) => {
                    if (isFrenchLevel(event.target.value))
                      setChoice({
                        forLevel: currentLevel ?? "a1",
                        value: event.target.value,
                      });
                  }}
                >
                  {FRENCH_LEVELS.map((item) => (
                    <option key={item} value={item}>
                      {item.toUpperCase()}
                    </option>
                  ))}
                </select>
              </label>
              <Button disabled={saving || selectedLevel === currentLevel}>
                {saving ? "Saving…" : "Save level"}
              </Button>
              <Link href="/settings" className="ml-3 text-xs text-violet-700">
                Settings
              </Link>
              {message && <FormMessage>{message}</FormMessage>}
              {error && <FormMessage error>{error}</FormMessage>}
            </form>
          </details>
        </Card>
      </div>
      <Card className="my-5" aria-label="Learning progress">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="panel-title">Your progress</h2>
          <Link href="/progress" className="text-xs text-violet-700">
            View learning progress →
          </Link>
        </div>
        {learningError ? (
          <p role="alert" className="mt-4 text-sm text-rose-700">
            {learningError}
          </p>
        ) : (
          <div className="progress-stats">
            {[
              ["Lessons completed", learning?.lessons_completed],
              ["Lessons in progress", learning?.lessons_in_progress],
              ["Exercises answered", learning?.total_answered_exercises],
            ].map(([label, value]) => (
              <div key={label}>
                <strong>{value ?? "—"}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        )}
        {learning && learning.total_answered_exercises > 0 && (
          <p className="mt-5 text-xs muted">
            Average completed session score:{" "}
            {learning.average_completed_session_score}%
          </p>
        )}
      </Card>
      <section className="quick-links" aria-label="Ways to practice">
        <Link href="/ai-tutor" className="quick-link">
          <Icon name="chat" />
          <div>
            <h3>Ask your AI Tutor</h3>
            <p>A question, a new word, a little conversation.</p>
          </div>
          <Icon name="arrow" />
        </Link>
        <Link href="/voice-practice" className="quick-link">
          <Icon name="mic" />
          <div>
            <h3>Practice speaking</h3>
            <p>Find your voice, one French sentence at a time.</p>
          </div>
          <Icon name="arrow" />
        </Link>
      </section>
    </main>
  );
}
