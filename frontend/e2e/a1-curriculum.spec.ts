import { enterExercises } from './learning-navigation';
import { expect, test } from "@playwright/test";

test("corrected A1 drafts render all ten packets and the revised book exercise", async ({ page }) => {
  test.skip(process.env.A1_E2E_REAL_API !== "1", "Requires an isolated corrected A1 API and synthetic reviewer account.");
  test.setTimeout(120_000);
  const email = process.env.A1_E2E_EMAIL;
  const password = process.env.A1_E2E_PASSWORD;
  const lessons = JSON.parse(process.env.A1_E2E_LESSONS ?? "[]") as { id: string; slug: string; title: string }[];
  expect(email && password && lessons.length === 10).toBeTruthy();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email!);
  await page.locator('input[autocomplete="current-password"]').fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto("/courses");
  await page.getByRole("link", { name: "View course", exact: true }).click();
  await expect(page.getByTestId("draft-lesson-label")).toHaveCount(10);
  for (const lesson of lessons) {
    const response = await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/lessons/${lesson.id}`);
    expect(response.status()).toBe(200);
    const detail = await response.json();
    expect(detail.content_status).toBe("draft");
    expect(detail.draft_preview).toBe(true);
    expect(JSON.stringify(detail)).not.toMatch(/"(?:is_correct|correct_option|accepted_answer)"\s*:/);
    await page.goto(`/lessons/${lesson.id}`);
    await expect(page.getByRole("heading", { name: lesson.title, exact: true })).toBeVisible();
    await expect(page.getByText(/Draft Preview/).first()).toBeVisible();
    if (lesson.slug === "a1-004") await expect(page.getByText(/When counting or saying dix/)).toBeVisible();
    if (lesson.slug === "a1-010") await expect(page.getByText(/There is no oi spelling/)).toBeVisible();
  }
  const articles = lessons.find((lesson) => lesson.slug === "a1-005")!;
  await page.goto(`/learn/${articles.id}`);
  await page.getByRole("button", { name: "Start or continue lesson" }).click();
  await expect(page).toHaveURL(/\/learning\/sessions\/[0-9a-f-]+$/);
  await enterExercises(page);
  const session = await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/learning/sessions/${page.url().split("/").at(-1)}`);
  expect((await session.json()).lesson_content_version).toBe("1.0.2");
  await expect(page.getByText("Which option means “a book”?", { exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main navigation" }).getByRole("link")).toHaveCount(5);
});
