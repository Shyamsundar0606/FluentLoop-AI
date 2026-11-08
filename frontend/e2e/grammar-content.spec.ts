import { expect, test, type Page } from '@playwright/test';
import { enterExercises } from './learning-navigation';

test.use({ trace: 'off' });
test.skip(process.env.M083_E2E !== '1', 'Requires the disposable 08.3 browser environment.');
const api = process.env.PLAYWRIGHT_API_BASE_URL;

async function login(page: Page, role: 'admin' | 'learner' | 'reviewer') {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env[`M083_${role.toUpperCase()}_EMAIL`]!);
  await page.locator('input[autocomplete="current-password"]').fill(process.env.M083_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const response = await page.request.get(`${api}/auth/me`);
  expect(response.status()).toBe(200);
  expect((await response.json()).user.role).toBe(role === 'reviewer' ? 'learner' : role);
}

test('draft lesson, listening replay, topic practice, and mistake review', async ({ page }) => {
  test.setTimeout(120_000);
  await login(page, 'admin');
  await page.goto('/courses?level=a1');
  await expect(page.getByRole('status', { name: 'Learning access' })).toContainText('Authorized draft preview');
  const lesson = page.getByRole('article').filter({ has: page.getByRole('heading', { name: 'Give and ask for a name', exact: true }) });
  await lesson.getByRole('link', { name: 'Start', exact: true }).click();
  await page.getByRole('button', { name: 'Start or continue lesson' }).click();
  await enterExercises(page);
  await page.getByRole('radio', { name: 'Je m’appelle Marie.', exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('heading', { name: 'Correct!', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Load French audio' }).click();
  const audio = page.getByLabel('French listening audio');
  await expect(audio).toBeVisible({ timeout: 45_000 });
  await expect.poll(() => audio.evaluate((element: HTMLAudioElement) => element.duration)).toBeGreaterThan(0);
  await audio.evaluate(async (element: HTMLAudioElement) => {
    await element.play();
    element.pause();
    element.currentTime = 0;
    await element.play();
    element.pause();
  });
  await page.getByRole('radio', { name: 'My name is Marie.', exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByLabel('Your answer').fill('Je suis Marie.');
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('heading', { name: 'Not quite.', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to completion' }).click();
  await page.getByRole('button', { name: 'Complete lesson' }).click();
  await page.getByRole('link', { name: 'Review mistakes' }).click();
  await expect(page.getByRole('region', { name: 'Mistake review' })).toContainText('Introduce yourself as Marie');

  await page.goto('/grammar?level=a1');
  const grammar = page.getByRole('region', { name: 'Grammar practice' });
  const picker = grammar.getByLabel('Grammar topic');
  const option = picker.getByRole('option', { name: /introduc/i });
  await expect(option).toHaveCount(1);
  await picker.focus();
  await expect(picker).toBeFocused();
  const topic = (await option.getAttribute('value'))!;
  await picker.selectOption(topic);
  await expect(grammar.getByRole('heading', { name: 'French examples' })).toBeVisible();
  for (const width of [320, 390, 768, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  const practice = grammar.getByRole('button', { name: 'Practice this grammar' });
  await practice.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/learning\/sessions\//);
  await page.getByRole('radio', { name: 'Je m’appelle Marie.', exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.route('**/exercises/*/audio', route => route.fulfill({
    status: 503, json: { detail: 'French audio is temporarily unavailable. Please retry.' },
    headers: { 'access-control-allow-origin': new URL(page.url()).origin, 'access-control-allow-credentials': 'true' },
  }), { times: 1 });
  await page.getByRole('button', { name: 'Load French audio' }).click();
  await expect(page.getByRole('button', { name: 'Retry audio' })).toBeVisible();
  await page.getByRole('button', { name: 'Retry audio' }).click();
  await expect(audio).toBeVisible();
  await page.getByRole('radio', { name: 'My name is Marie.', exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByLabel('Your answer').fill("Je m'appelle Marie.");
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await page.getByRole('button', { name: 'Continue to completion' }).click();
  await page.getByRole('button', { name: 'Complete practice' }).click();
  await expect(page.getByRole('region', { name: 'Saved results' })).toContainText('100%');
  await page.reload();
  await page.getByRole('link', { name: 'Back to grammar topic' }).click();
  await expect(picker).toHaveValue(topic);
  await grammar.getByRole('button', { name: 'Ask AI Tutor' }).click();
  await expect(page).toHaveURL(/\/ai-tutor\/[0-9a-f-]+$/);
  await page.goto(`/grammar?level=a1&topic=${topic}`);
  await grammar.getByRole('button', { name: 'Practice speaking' }).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\//);
});

test('learner cannot fetch draft grammar or use the direct lesson URL', async ({ page }) => {
  await login(page, 'learner');
  await page.goto('/grammar?level=a1');
  await expect(page.getByRole('status', { name: 'Learning access' })).toContainText('Published content only');
  const grammar = await page.request.get(`${api}/learning/grammar?level=A1`);
  expect((await grammar.json()).items).toEqual([]);
  const lessonId = process.env.M083_LESSON_ID!;
  expect((await page.request.get(`${api}/lessons/${lessonId}`)).status()).toBe(404);
  await page.goto(`/learn/${lessonId}`);
  await expect(page.getByText('Lesson not found.', { exact: true })).toBeVisible();
  await page.goto('/profile/curriculum-review');
  await expect(page.getByText('Curriculum review access required.', { exact: true })).toBeVisible();
});

test('an explicitly granted reviewer can record a versioned finding', async ({ page }) => {
  await login(page, 'reviewer');
  await page.goto('/profile/curriculum-review');
  await page.getByRole('button', { name: /A1 grammar and everyday French/ }).click();
  await page.getByLabel('Findings').fill('Synthetic browser check of a language review.');
  await page.getByLabel('Required corrections').fill('A synthetic finding for disposable verification.');
  await page.getByRole('button', { name: 'Save review decision' }).click();
  await expect(page.getByText('Review decision saved.')).toBeVisible();
  await page.getByText('Decision history', { exact: true }).click();
  await expect(page.getByText(/Synthetic browser check of a language review/)).toBeVisible();
});
