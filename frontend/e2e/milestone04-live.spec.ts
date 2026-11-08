import { enterExercises } from './learning-navigation';
import { expect, test } from '@playwright/test';

const email = process.env.M04_LIVE_EMAIL;
const password = process.env.M04_LIVE_PASSWORD;
const learnerEmail = process.env.M04_LEARNER_EMAIL;
const learnerPassword = process.env.M04_LEARNER_PASSWORD;
const lessonId = process.env.M04_LIVE_LESSON_ID;
const optionsByOrder = JSON.parse(process.env.M04_LIVE_OPTIONS ?? '[]') as {
  correct_id: string;
  wrong_id: string;
}[];

test('live authorized draft lesson flow, persistence, idempotency, and learner denial', async ({ page }) => {
  test.skip(
    !email || !password || !learnerEmail || !learnerPassword || !lessonId || optionsByOrder.length < 5,
    'Requires the isolated Milestone 04 live-test stack and seeded test accounts.',
  );
  test.setTimeout(120_000);

  const apiBase = process.env.M04_LIVE_API_BASE ?? 'http://127.0.0.1:8001/api/v1';
  const apiOrigin = new URL(apiBase).origin;
  const frontendOrigin = process.env.M04_LIVE_FRONTEND_ORIGIN ?? 'http://127.0.0.1:3001';

  async function signIn(loginEmail: string, loginPassword: string) {
    await page.goto('/login');
    await page.getByLabel('Email').fill(loginEmail);
    await page.locator('input[autocomplete="current-password"]').fill(loginPassword);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
  }

  await signIn(email!, password!);
  await page.goto('/courses');
  await expect(page.getByText('No published A1 courses yet')).not.toBeVisible();
  await expect(page.getByText('Draft Preview · unreviewed', { exact: true })).toHaveCount(1);
  await page.getByRole('link', { name: 'View course' }).click();
  await expect(page.getByTestId('draft-lesson-label')).toHaveCount(10);
  await page.goto(`/learn/${lessonId}`);
  await expect(page.getByRole('heading', { name: 'Introducing Yourself' })).toBeVisible();
  await expect(page.getByText('Draft Preview', { exact: false }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Start or continue lesson' }).click();
  await expect(page).toHaveURL(/\/learning\/sessions\/[0-9a-f-]+$/i);
  await enterExercises(page);
  const sessionId = page.url().split('/').at(-1)!;
  await expect(page.getByText('Draft Preview', { exact: false }).first()).toBeVisible();

  const firstOption = page.locator(`input[value="${optionsByOrder[0].correct_id}"]`);
  await expect(firstOption).toHaveCount(1);
  await firstOption.check();
  let firstSubmission: { url: string; payload: Record<string, unknown> } | undefined;
  const onRequest = (request: import('@playwright/test').Request) => {
    if (request.url().endsWith(`/learning/sessions/${sessionId}/answers`) && request.method() === 'POST') {
      firstSubmission = { url: request.url(), payload: request.postDataJSON() as Record<string, unknown> };
    }
  };
  page.on('request', onRequest);
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('heading', { name: 'Correct!' })).toBeVisible();
  page.off('request', onRequest);
  expect(firstSubmission).toBeDefined();

  const csrf = (await page.context().cookies(apiOrigin))
    .find((cookie) => cookie.name.endsWith('_csrf'))?.value;
  expect(csrf).toBeTruthy();
  const duplicate = await page.context().request.post(firstSubmission!.url, {
    data: firstSubmission!.payload,
    headers: { Origin: frontendOrigin, 'X-CSRF-Token': csrf! },
  });
  expect(duplicate.status()).toBe(200);
  const replay = await duplicate.json();
  expect(replay.idempotent_replay).toBe(true);
  expect(replay.score_points).toBe(1);

  await page.getByRole('button', { name: 'Continue' }).click();
  await page.locator(`input[value="${optionsByOrder[1].wrong_id}"]`).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('heading', { name: 'Not quite.' })).toBeVisible();
  await expect(
    page.getByRole('region', { name: 'Exercise' }).getByText(/^Correct answer:/).first(),
  ).toBeVisible();

  await page.reload();
  await expect(page.getByRole('heading', { name: 'Not quite.' })).toBeVisible();
  await expect(page.getByText('2 / 5 answered')).toBeVisible();

  for (const item of optionsByOrder.slice(2)) {
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.locator(`input[value="${item.correct_id}"]`).check();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await expect(page.getByRole('heading', { name: 'Correct!' })).toBeVisible();
  }

  await page.getByRole('button', { name: 'Continue to completion' }).click();
  await page.getByRole('button', { name: 'Complete lesson' }).click();
  await expect(page).toHaveURL(new RegExp(`/learning/results/${sessionId}$`));
  await expect(page.getByText('80%', { exact: true })).toBeVisible();
  await expect(page.getByText('4 correct · 1 incorrect · 5 questions')).toBeVisible();

  await page.getByRole('link', { name: /Dashboard/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.locator('.signout-button:visible').click();
  await expect(page).toHaveURL(/\/login/);
  await signIn(email!, password!);
  await page.goto('/dashboard');
  const metrics = page.getByRole('region', { name: 'Learning progress' });
  await expect(metrics.locator('.progress-stats > div').filter({ hasText: 'Lessons completed' })).toContainText('1');
  const answeredCount = await metrics.locator('.progress-stats > div').filter({ hasText: 'Exercises answered' }).innerText();
  expect(Number(answeredCount.match(/\d+/)?.[0])).toBeGreaterThanOrEqual(5);
  await expect(metrics.getByText(/Average completed session score:/)).toContainText('80%');
  await page.goto('/progress');
  await expect(page.getByText('A1', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('completed', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('80%', { exact: false }).first()).toBeVisible();

  await page.goto('/dashboard');
  await page.locator('.signout-button:visible').click();
  await expect(page).toHaveURL(/\/login/);
  await signIn(learnerEmail!, learnerPassword!);

  const courseList = await page.context().request.get(`${apiBase}/courses?level=A1`);
  expect(courseList.status()).toBe(200);
  expect((await courseList.json()).items).toHaveLength(0);
  const draftLesson = await page.context().request.get(`${apiBase}/lessons/${lessonId}`);
  expect(draftLesson.status()).toBe(404);
  const protectedSession = await page.context().request.get(`${apiBase}/learning/sessions/${sessionId}`);
  expect(protectedSession.status()).toBe(404);
  expect((await protectedSession.text()).toLowerCase()).not.toContain('correct_answer');

  const learnerCsrf = (await page.context().cookies(apiOrigin))
    .find((cookie) => cookie.name.endsWith('_csrf'))?.value;
  const protectedAnswer = await page.context().request.post(
    `${apiBase}/learning/sessions/${sessionId}/answers`,
    {
      data: firstSubmission!.payload,
      headers: { Origin: frontendOrigin, 'X-CSRF-Token': learnerCsrf! },
    },
  );
  expect(protectedAnswer.status()).toBe(404);
});
