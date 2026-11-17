import { expect, test, type Page } from "@playwright/test";
import type { LearningSession } from "../lib/learning";
import type { WritingSubmission } from "../lib/assessments";

const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
const sessionId = "a1111111-1111-4111-8111-111111111111";
const lessonId = "b2222222-2222-4222-8222-222222222222";

async function mockAssessments(page: Page, { empty = false, unavailable = false } = {}) {
  await page.route(`${api}/**`, async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = {
      "access-control-allow-origin": new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin,
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "access-control-allow-headers": "content-type,x-csrf-token",
    };
    if (request.method() === "OPTIONS") { await route.fulfill({ status: 200, headers }); return; }
    let body: unknown = {};
    let status = 200;
    if (path.endsWith("/auth/me")) body = { user: {
      id: "learner", email: "assessment@example.test", role: "learner", email_verified: true,
      display_name: "Learner", native_language: "English", timezone: "Europe/Paris", onboarding_completed: true,
      preferences: { current_level: "a1", daily_study_minutes: 15, learning_focus: "balanced", theme: "light" },
    } };
    else if (path.endsWith("/learning/access")) body = { mode: "published_only" };
    else if (path.endsWith("/writing/history")) body = { items: [], next_offset: null };
    else if (path.endsWith("/assessments/history")) body = { items: empty ? [] : [{
      id: sessionId, skill: "grammar", title: "Saved grammar assessment", level: "A1", status: "completed",
      started_at: "2026-11-15T12:00:00Z", answered: 3, question_count: 3,
      score_points: 2, max_score_points: 3, draft_preview: false,
    }], next_offset: null };
    else if (path.endsWith("/assessments/sessions")) {
      expect(request.postDataJSON()).toEqual({ skill: "grammar", lesson_id: lessonId });
      status = 503; body = { detail: "Assessment service unavailable. Please retry." };
    } else if (path.endsWith("/learning/assessments")) {
      status = unavailable ? 503 : 200;
      body = unavailable ? { detail: "Unavailable" } : { level: "A1", draft_preview: false, items: empty ? [] : [{
        id: `grammar:${lessonId}`, lesson_id: lessonId, skill: "grammar", title: "Present tense",
        level: "A1", question_count: 3, duration_minutes: 6, content_version: "v1", scoring_policy: "objective-v1",
      }] };
    }
    await route.fulfill({ status, headers, contentType: "application/json", body: JSON.stringify(body) });
  });
}

test("assessment selection and saved history remain usable on mobile and recover from start failure", async ({ page }) => {
  await mockAssessments(page);
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/assessments");
  await expect(page.getByRole("heading", { name: "Skills assessments" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main navigation" }).getByRole("link")).toHaveCount(5);
  await expect(page.getByRole("link", { name: "View results · 2 / 3" })).toHaveAttribute("href", `/learning/results/${sessionId}`);
  const start = page.getByRole("button", { name: "Start or resume grammar assessment" });
  await start.focus();
  await expect(start).toBeFocused();
  await start.press("Enter");
  await expect(page.getByRole("alert").filter({ hasText: "Assessment service unavailable" })).toHaveText("Assessment service unavailable. Please retry.");
  await expect(start).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("ordinary learner sees an honest empty state", async ({ page }) => {
  await mockAssessments(page, { empty: true });
  await page.goto("/assessments");
  await expect(page.getByText("No authorized assessments are available at this level yet.")).toBeVisible();
  await expect(page.getByText("No assessment history yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Start or resume/ })).toHaveCount(0);
});

test("failed catalog request announces recovery", async ({ page }) => {
  await mockAssessments(page, { unavailable: true });
  await page.goto("/assessments");
  await expect(page.getByRole("alert").filter({ hasText: "Assessments could not load" })).toHaveText("Assessments could not load. Refresh to retry.");
});

test("assessment uses shared questions, preserves answers on reload and returns to assessments", async ({ page }) => {
  await mockAssessments(page);
  const exerciseId = "c3333333-3333-4333-8333-333333333333";
  const optionId = "d4444444-4444-4444-8444-444444444444";
  const session: LearningSession = {
    id: sessionId, lesson_id: lessonId, lesson_content_version: "v1", cefr_level: "A1",
    activity_key: "assessment:grammar:objective-v1", status: "in_progress", preview_mode: false,
    started_at: "2026-11-15T12:00:00Z", last_activity_at: "2026-11-15T12:00:00Z", completed_at: null,
    current_section_position: 0, current_exercise_position: 0, total_exercises: 1,
    answered_exercises: 0, score_points: 0, max_score_points: 1, percentage: 0,
    lesson: { id: lessonId, title: "Present tense", description: "French grammar practice", level: "A1",
      content_version: "v1", estimated_minutes: 2, course_title: "French A1", unit_title: "Introductions",
      objectives: [], sections: [], vocabulary: [], grammar: [], dialogues: [] },
    exercises: [{ id: exerciseId, exercise_id: exerciseId, exercise_order: 1, type: "multiple_choice",
      prompt: "Je ___ ici.", instructions: "Choose the form of être.", answered: false, feedback: null,
      options: [{ id: optionId, text: "suis", sequence_order: 1 }] }],
  };
  await page.route(`${api}/learning/assessments/sessions`, async route => {
    if (route.request().method() === "OPTIONS") { await route.fallback(); return; }
    expect(route.request().postDataJSON()).toEqual({ skill: "grammar", lesson_id: lessonId });
    await route.fulfill({ json: session, headers: {
      "access-control-allow-origin": new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin,
      "access-control-allow-credentials": "true",
    } });
  });
  await page.route(`${api}/learning/sessions/${sessionId}**`, async route => {
    if (route.request().method() === "OPTIONS") { await route.fallback(); return; }
    if (new URL(route.request().url()).pathname.endsWith("/answers")) {
      expect(route.request().postDataJSON()).toMatchObject({ session_exercise_id: exerciseId, selected_option_id: optionId });
      session.current_exercise_position = 1; session.answered_exercises = 1; session.score_points = 1;
      session.exercises[0].answered = true;
      session.exercises[0].submitted_answer = { selected_option_id: optionId };
      session.exercises[0].feedback = { is_correct: true, correct_answer: "suis", explanation: "With je, use suis.",
        awarded_points: 1, max_points: 1, answered_at: "2026-11-15T12:01:00Z" };
    }
    await route.fulfill({ json: session, headers: {
      "access-control-allow-origin": new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin,
      "access-control-allow-credentials": "true",
    } });
  });
  await page.goto("/assessments");
  await page.getByRole("button", { name: "Start or resume grammar assessment" }).click();
  await expect(page).toHaveURL(new RegExp(`/learning/sessions/${sessionId}$`));
  await page.getByRole("radio", { name: "suis", exact: true }).check();
  await page.getByRole("button", { name: "Submit answer", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Correct!", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("With je, use suis.", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Continue to completion" }).click();
  await expect(page.getByRole("button", { name: "Complete assessment", exact: true })).toBeVisible();
  await page.getByRole("link", { name: /Save and exit/ }).click();
  await expect(page).toHaveURL(/\/assessments$/);
});

test("writing preserves the original, retries advisory feedback and saves revisions separately", async ({ page }) => {
  await mockAssessments(page);
  const headers = {
    "access-control-allow-origin": new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin,
    "access-control-allow-credentials": "true",
  };
  const rows: WritingSubmission[] = [];
  let feedbackRequests = 0;
  await page.route(`${api}/learning/assessments/writing**`, async route => {
    const request = route.request();
    if (request.method() === "OPTIONS") { await route.fallback(); return; }
    const path = new URL(request.url()).pathname;
    let body: unknown;
    if (path.includes("/tasks/")) body = { lesson_id: lessonId, title: "Introduce yourself", level: "A1",
      content_version: "0.1.0", prompt: "Write three simple French sentences about a fictional person.", draft_preview: true };
    else if (path.endsWith("/feedback")) {
      feedbackRequests += 1;
      const row = rows.find(item => path.includes(item.id))!;
      row.feedback_status = feedbackRequests === 1 ? "unavailable" : "available";
      row.advisory_feedback = feedbackRequests === 1 ? null : { task_completion: "Three sentences address the task.",
        grammar_suggestions: [], vocabulary_suggestions: ["Try another activity word."], clarity: "The introduction is clear." };
      body = row;
    } else if (path.endsWith("/history")) body = { items: rows, next_offset: null };
    else if (request.method() === "POST") {
      const submitted = request.postDataJSON();
      expect(submitted.lesson_id).toBe(lessonId);
      expect(submitted.idempotency_key).toMatch(/^[0-9a-f-]{36}$/);
      const row: WritingSubmission = { id: crypto.randomUUID(), lesson_id: lessonId, level: "A1",
        content_version: "0.1.0", prompt: "Write three simple French sentences about a fictional person.",
        original_text: submitted.text, created_at: "2026-11-15T12:00:00Z", draft_preview: true,
        feedback_status: "not_requested", advisory_feedback: null, notice: "Advisory feedback only." };
      rows.push(row); body = row;
    } else body = rows.find(item => path.endsWith(item.id));
    await route.fulfill({ json: body, headers });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/assessments/writing/${lessonId}`);
  const original = "Je m'appelle Lina. J'habite à Lyon. J'aime lire.";
  await page.getByLabel("Your French response").fill(original);
  await page.getByRole("button", { name: "Save writing", exact: true }).click();
  await expect(page).toHaveURL(/submission=/);
  await page.reload();
  await expect(page.getByText(original, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Request optional AI feedback" }).click();
  await expect(page.getByRole("status").filter({ hasText: "AI feedback is unavailable" })).toBeVisible();
  await expect(page.getByText(original, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Request optional AI feedback" }).click();
  await expect(page.getByRole("heading", { name: "Advisory AI feedback" })).toBeVisible();
  await page.getByRole("button", { name: "Write a revision as a new submission" }).click();
  await page.getByLabel("Your French response").fill(original + " J'aime aussi marcher.");
  await page.getByRole("button", { name: "Save writing", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your saved original response" })).toBeVisible();
  expect(rows).toHaveLength(2);
  expect(rows[0].original_text).toBe(original);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
