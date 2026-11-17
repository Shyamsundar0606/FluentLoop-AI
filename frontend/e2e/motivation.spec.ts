import { expect, test } from "@playwright/test";

test("optional dashboard rewards update without duplication and retain opt-out (mock API)", async ({ page }) => {
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
  const origin = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin;
  let enabled = true;
  let xp = 0;
  await page.route(`${api}/**`, async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = { "access-control-allow-origin": origin, "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,POST,PATCH,OPTIONS", "access-control-allow-headers": "content-type,x-csrf-token" };
    if (request.method() === "OPTIONS") { await route.fulfill({ status: 200, headers }); return; }
    let body: unknown = {};
    if (path.endsWith("/auth/me")) body = { user: { id: "learner", email: "reward@example.test", role: "learner", email_verified: true,
      display_name: "Learner", native_language: "English", onboarding_completed: true,
      preferences: { current_level: "a1", daily_study_minutes: 15, theme: "light" } } };
    else if (path.endsWith("/learning/dashboard")) body = { active_sessions: [], lessons_started: 0, lessons_completed: 0,
      lessons_in_progress: 0, total_answered_exercises: 0, average_completed_session_score: 0, recent_activity: [], learning_path: [] };
    else if (path.endsWith("/courses")) body = { items: [], total: 0 };
    else if (path.endsWith("/study/today")) body = null;
    else if (path.endsWith("/users/me/preferences")) { enabled = request.postDataJSON().motivation_enabled; body = { motivation_enabled: enabled }; }
    else if (path.endsWith("/motivation/history")) body = { items: xp ? [{ id: "reward", kind: "lesson", xp: 20, study_date: "2026-11-15" }] : [], next_offset: null };
    else if (path.includes("/study/motivation")) {
      if (path.endsWith("/sync")) xp = 20;
      body = { enabled, timezone: "Europe/Paris", total_xp: xp, today_activities: xp ? 1 : 0, current_streak: xp ? 1 : 0,
        best_streak: xp ? 1 : 0, xp_policy: { lesson: 20 }, notice: "XP records activities, not proficiency.",
        achievements: xp ? [{ key: "first_lesson", title: "First lesson completed", earned_at: "2026-11-15T12:00:00Z" }] : [] };
    }
    await route.fulfill({ json: body, headers });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  const panel = page.getByRole("region", { name: "Learning motivation" });
  await expect(panel).toContainText("0 XP");
  const update = panel.getByRole("button", { name: "Update rewards from completed activities" });
  await update.focus();
  await update.press("Enter");
  await expect(panel).toContainText("20 XP");
  await update.click();
  await expect(panel).toContainText("20 XP");
  await panel.getByText("Earned achievements", { exact: true }).click();
  await expect(panel.getByText(/First lesson completed/)).toBeVisible();
  await panel.getByRole("button", { name: "Disable motivational features" }).click();
  await expect(panel).toContainText("Motivational features are disabled.");
  await page.reload();
  await expect(panel.getByRole("button", { name: "Enable motivational features" })).toBeVisible();
  await panel.getByRole("button", { name: "Enable motivational features" }).click();
  await expect(panel).toContainText("20 XP");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
