import { expect, test, Page } from "@playwright/test";
import { mkdirSync } from "node:fs";

const cid = "a1111111-1111-4111-8111-111111111111";
const other = "b2222222-2222-4222-8222-222222222222";
const now = "2026-11-02T15:00:00Z";
const user = {
  id: "learner",
  email: "learner@example.test",
  role: "learner",
  email_verified: true,
  display_name: "Learner",
  preferred_name: null,
  native_language: "English",
  onboarding_completed: true,
  preferences: {
    current_level: "a1",
    explanation_language: "English",
    target_language: "French",
    daily_study_minutes: 15,
    theme: "system",
    learning_focus: "balanced",
    audio_playback_speed: 1,
  },
};

async function mockTutor(
  page: Page,
  { offline = false, preview = false, authenticated = true } = {},
) {
  let mode = "tutor";
  let archived = false;
  const messages: Record<string, unknown>[] = [];
  const conversation = () => ({
    id: cid,
    title: "French practice",
    mode,
    cefr_level: "A1",
    status: archived ? "archived" : "active",
    scenario_id: mode === "roleplay" ? "a1-boulangerie" : null,
    preview_mode: preview,
    updated_at: now,
    messages,
    has_more_messages: false,
  });
  await page.route(
    `${process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1"}/**`,
    async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      const method = request.method();
      const headers = {
        "access-control-allow-origin": new URL(
          process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001",
        ).origin,
        "access-control-allow-credentials": "true",
        "access-control-allow-methods": "GET,POST,PATCH,OPTIONS",
        "access-control-allow-headers": "content-type,x-csrf-token",
      };
      if (method === "OPTIONS") {
        await route.fulfill({ status: 200, headers });
        return;
      }
      let body: unknown = {};
      let status = 200;
      if (path.endsWith("/auth/me")) {
        body = authenticated
          ? { user }
          : { detail: "Authentication required." };
        status = authenticated ? 200 : 401;
      } else if (path.endsWith("/ai/health"))
        body = {
          available: !offline,
          message: offline
            ? "Configured model unavailable. Regular lessons remain available."
            : "Ready",
        };
      else if (path.endsWith(`/conversations/${other}`)) {
        status = 404;
        body = { detail: "Conversation not found." };
      } else if (path.endsWith("/messages")) {
        if (offline) {
          status = 503;
          body = {
            detail: "The tutor is unavailable. Retry with the same request ID.",
          };
        } else {
          const payload = request.postDataJSON();
          messages.push({
            id: crypto.randomUUID(),
            role: "user",
            content: payload.message,
            response_status: "success",
            grounding_status: "unverified",
            request_id: payload.request_id,
            sources: [],
            correction: null,
          });
          const correction =
            mode === "correction"
              ? {
                  original_text: payload.message,
                  corrected_text: "J'ai 24 ans.",
                  has_errors: true,
                  explanations: ["Use avoir for age."],
                  alternative_expressions: ["Je viens de fêter mes 24 ans."],
                }
              : null;
          messages.push({
            id: crypto.randomUUID(),
            role: "assistant",
            content: correction
              ? "Corrected: J'ai 24 ans.\nUse avoir for age."
              : "Bonjour! Être means to be; avoir means to have.",
            response_status: "success",
            grounding_status: preview ? "draft_preview" : "curriculum_context",
            sources: [
              {
                lesson_id: "lesson-1",
                title: "Greetings lesson",
                url: "/lessons/lesson-1",
                draft_preview: preview,
              },
            ],
            correction,
          });
          body = { answer: messages.at(-1)?.content };
        }
      } else if (path.endsWith("/archive")) {
        archived = true;
        body = conversation();
      } else if (path.endsWith("/ai/conversations")) {
        if (method === "POST") {
          mode = request.postDataJSON().mode;
          body = conversation();
          status = 201;
        } else body = [conversation()];
      } else if (path.endsWith(`/conversations/${cid}`)) body = conversation();
      else if (path.endsWith("/ai/scenarios"))
        body = [
          {
            id: "a1-boulangerie",
            title: "Ordering at a boulangerie",
            cefr_level: "A1",
            description: "Buy bread.",
            tutor_role: "shop assistant",
            learner_role: "customer",
            provenance: "Original practice prompt",
            suggested_vocabulary: ["une baguette"],
          },
        ];
      else if (path.endsWith("/start")) {
        mode = "roleplay";
        body = conversation();
        status = 201;
      } else if (path.includes("/ai/recommendations"))
        body = [
          {
            id: "r1",
            topic: "Getting started",
            reason: "Not enough repeated-error evidence.",
            cefr_level: "A1",
            lesson: null,
            suggested_action: "Ask the tutor",
          },
        ];
      await route.fulfill({
        status,
        headers,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  );
}

test("start, send, follow up, refresh, resume history and archive (mock API)", async ({
  page,
}) => {
  await mockTutor(page);
  await page.goto("/ai-tutor");
  await page.getByLabel("Practice mode").selectOption("grammar");
  await page.getByLabel("Your question").fill("Explain être");
  await page.getByRole("button", { name: "Start a new conversation" }).click();
  await expect(page).toHaveURL(new RegExp(cid));
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Être means to be");
  if (process.env.UI_SCREENSHOTS === "1") {
    mkdirSync("../docs/verification/frontend-redesign", { recursive: true });
    await page.screenshot({
      path: "../docs/verification/frontend-redesign/tutor-chat.png",
      fullPage: true,
    });
  }
  await expect(
    page.getByRole("link", { name: "Greetings lesson" }),
  ).toHaveAttribute("href", "/lessons/lesson-1");
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Another example?");
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .press("Enter");
  await expect(
    page
      .getByRole("list", { name: "Conversation messages" })
      .getByText("Another example?", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Another example?");
  await page.getByRole("link", { name: "History", exact: true }).click();
  await page.getByLabel("Filter by mode").selectOption("grammar");
  await page
    .getByRole("link", { name: "French practice", exact: true })
    .click();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Être");
  await page.goto("/ai-tutor/history");
  await page.getByRole("button", { name: "Archive", exact: true }).click();
  await expect(page.getByText(/grammar · archived/)).toBeVisible();
});

test("correction feedback and original text (mock API)", async ({ page }) => {
  await mockTutor(page);
  await page.goto("/ai-tutor");
  await page.getByLabel("Practice mode").selectOption("correction");
  await page.getByLabel("Your question").fill("Je suis 24 ans.");
  await page.getByRole("button", { name: "Start a new conversation" }).click();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("Original: Je suis 24 ans.")).toBeVisible();
  await expect(page.getByText(/Stylistic alternative/)).toBeVisible();
});

test("scenario start and evidence-based recommendation empty state (mock API)", async ({
  page,
}) => {
  await mockTutor(page);
  await page.goto("/ai-tutor/scenarios");
  await page.getByRole("button", { name: "Start practice" }).click();
  await expect(page).toHaveURL(new RegExp(cid));
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Bonjour");
  await page.goto("/ai-tutor/recommendations");
  await page.getByRole("button", { name: "Refresh recommendations" }).click();
  await expect(
    page.getByText("Not enough repeated-error evidence."),
  ).toBeVisible();
});

test("offline status and saved retry (mock API)", async ({ page }) => {
  await mockTutor(page, { offline: true });
  await page.goto("/ai-tutor");
  await expect(page.getByRole("status")).toContainText("unavailable");
  await page.getByLabel("Your question").fill("Bonjour");
  await page.getByRole("button", { name: "Start a new conversation" }).click();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.locator('p[role="alert"]')).toContainText("unavailable");
  await expect(
    page.getByRole("button", { name: "Retry saved message" }),
  ).toBeVisible();
});

test("preview labeling and cross-owner denial presentation (mock API)", async ({
  page,
}) => {
  await mockTutor(page, { preview: true });
  await page.goto(`/ai-tutor/${cid}`);
  await expect(
    page.getByText(/Draft preview: this conversation/),
  ).toBeVisible();
  await page.goto(`/ai-tutor/${other}`);
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "Conversation not found.",
  );
  await expect(page.getByLabel("Conversation messages")).toHaveCount(0);
});

test("unauthenticated tutor redirects to login (mock API)", async ({
  page,
}) => {
  await mockTutor(page, { authenticated: false });
  await page.goto("/ai-tutor");
  await expect(page).toHaveURL(/\/login\?next=/);
});
