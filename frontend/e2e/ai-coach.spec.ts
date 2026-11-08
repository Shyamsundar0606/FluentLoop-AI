import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

const capture = resolve("../.speech-data/m08_1/conversation-capture.wav");
const api = process.env.PLAYWRIGHT_API_BASE_URL;
test.use({
  trace: "off",
  permissions: ["microphone"],
  launchOptions: { args: [
    "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
    `--use-file-for-fake-audio-capture=${capture}`,
  ] },
});
test.skip(process.env.M09_E2E !== "1", "Requires the disposable coach environment.");

async function login(page: Page, account = "M083_LEARNER_EMAIL") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(process.env[account]!);
  await page.locator('input[autocomplete="current-password"]').fill(process.env.M083_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  expect((await (await page.request.get(`${api}/auth/me`)).json()).user.role).toBe("learner");
}

async function bakery(page: Page) {
  await page.goto("/ai-tutor/scenarios");
  return page.getByRole("article").filter({ has: page.getByRole("heading", { name: /boulangerie/i }) });
}

test("ordinary learner completes a real Ollama conversation and resumes its private summary", async ({ page, browser }) => {
  test.setTimeout(180_000);
  await login(page);
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "AI Tutor" }).click();
  await expect(page.getByRole("heading", { name: "AI French Tutor" })).toBeVisible();
  await (await bakery(page)).getByRole("button", { name: "Start text practice" }).click();
  const transcript = page.getByRole("list", { name: "Conversation messages" });
  await expect(transcript).toContainText("Qu’est-ce que vous désirez ?");
  await page.getByLabel("Difficulty").selectOption("easier");
  await page.getByLabel("Corrections").selectOption("after");
  const id = page.url().split("/").at(-1)!;
  await page.setViewportSize({ width: 390, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  for (const message of [
    "Bonjour, je voudrais une baguette, s’il vous plaît.",
    "Pouvez-vous expliquer brièvement pourquoi on dit je voudrais ?",
  ]) {
    await page.getByRole("textbox", { name: "Message" }).fill(message);
    const response = page.waitForResponse(r => r.url().endsWith(`/${id}/messages`) && r.request().method() === "POST");
    await page.getByRole("textbox", { name: "Message" }).press("Enter");
    const answer = await response;
    expect(answer.status()).toBe(200);
    const data = await answer.json();
    expect(data.answer.trim()).not.toBe("");
    expect(data.grounding_status).toBe("general_knowledge");
    expect(data.sources).toEqual([]);
  }
  await page.getByRole("button", { name: "Finish conversation" }).click();
  await expect(page.getByRole("heading", { name: "Conversation summary" })).toBeVisible();
  await expect(page.getByText(/5 saved messages · 2 learner turns/)).toBeVisible();
  await expect(page.getByText(/Words used in your messages/)).toContainText("une baguette");
  await page.goto("/ai-tutor/history");
  await page.getByRole("link", { name: /boulangerie/i }).click();
  await expect(page.getByRole("heading", { name: "Conversation summary" })).toBeVisible();
  const other = await browser.newContext();
  try {
    const stranger = await other.newPage();
    await login(stranger, "M083_REVIEWER_EMAIL");
    expect((await stranger.request.get(`${api}/ai/conversations/${id}/coach`)).status()).toBe(404);
  } finally {
    await other.close();
  }
});

test("scenario voice recording uses local transcription, tutor inference and playback", async ({ page }) => {
  test.skip(!existsSync(capture), "Requires the ignored synthetic French microphone fixture.");
  test.setTimeout(180_000);
  await login(page);
  await (await bakery(page)).getByRole("button", { name: "Start speaking" }).click();
  await expect(page.getByText("Bonjour ! Qu’est-ce que vous désirez ?")).toBeVisible();
  await page.getByRole("button", { name: "Record French", exact: true }).click();
  await expect(page.getByRole("button", { name: "Stop recording", exact: true })).toBeVisible();
  await page.waitForTimeout(6000); // Capture the actual French fixture from the browser's microphone stream.
  await page.getByRole("button", { name: "Stop recording", exact: true }).click();
  const turn = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/turns"));
  await page.getByRole("button", { name: "Send recording", exact: true }).click();
  const response = await turn;
  expect(response.status()).toBe(200);
  const saved = await response.json();
  expect(saved.transcription.model).toBe("base");
  expect(saved.transcript).toMatch(/je suis/i);
  if (saved.transcription_status === "uncertain") {
    await page.getByRole("button", { name: "Confirm and send", exact: true }).click();
  }
  const playback = page.getByRole("button", { name: "Play tutor audio", exact: true }).last();
  await expect(playback).toBeVisible({ timeout: 90_000 });
  await playback.click();
  await page.reload();
  await expect(playback).toBeVisible();
  await page.getByRole("link", { name: "Open shared transcript and coach options" }).click();
  await expect(page.getByRole("list", { name: "Conversation messages" })).toContainText(/je suis/i);
});
