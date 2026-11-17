import { expect, test } from "@playwright/test";

test("settings preserve motivation choice with keyboard access at mobile widths (mock API)", async ({ page }) => {
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
  const origin = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin;
  let preferences = { explanation_language: "English", target_language: "French", current_level: "a1",
    target_level: null, daily_study_minutes: 15, learning_focus: "balanced", theme: "light",
    audio_playback_speed: 1, motivation_enabled: true };
  await page.route(`${api}/**`, async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = { "access-control-allow-origin": origin, "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,PATCH,OPTIONS", "access-control-allow-headers": "content-type,x-csrf-token" };
    if (request.method() === "OPTIONS") { await route.fulfill({ status: 200, headers }); return; }
    let body: unknown = {};
    if (path.endsWith("/auth/me")) body = { user: { id: "settings-learner", email: "settings@example.test", role: "learner",
      display_name: "Learner", email_verified: true, onboarding_completed: true, preferences } };
    if (path.endsWith("/auth/sessions")) body = { sessions: [] };
    if (path.endsWith("/users/me/preferences")) {
      if (request.method() === "PATCH") preferences = request.postDataJSON();
      body = preferences;
    }
    await route.fulfill({ json: body, headers });
  });
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto("/settings");
  const choice = page.getByRole("checkbox", { name: "Show XP, streaks and achievements" });
  await expect(choice).toBeChecked();
  await choice.focus();
  await choice.press("Space");
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByText("Preferences saved.")).toBeVisible();
  await page.reload();
  await expect(choice).not.toBeChecked();
  await expect(page.getByRole("region", { name: "Your learning data" })).toContainText("Saved learning records remain retained.");
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await expect(nav.getByRole("link")).toHaveText(["Home", "Learn", "AI Tutor", "Speak", "Profile"]);
  await expect(nav.locator('[aria-current="page"]')).toHaveText("Profile");
  await page.getByRole("link", { name: "Skip to content" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#page-content")).toBeFocused();
  for (const width of [320, 390, 900, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
});
