import { enterExercises } from './learning-navigation';
import { test, expect, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const base = process.env.PLAYWRIGHT_API_BASE_URL ?? '';
const csrfName = process.env.PLAYWRIGHT_CSRF_COOKIE_NAME ?? 'fluentloop_csrf';
test.use({ trace: 'off' });
type Fixture = { admin: string; learner: string; lesson_id: string; password: string };
let fixture: Fixture;
test.beforeEach(() => {
  test.skip(process.env.M08_E2E_REAL_API !== '1', 'Requires the existing isolated M08 API/PostgreSQL.');
  fixture = process.env.M083_E2E === '1'
    ? { admin: process.env.M083_ADMIN_EMAIL!, learner: process.env.M083_LEARNER_EMAIL!,
        password: process.env.M083_PASSWORD!, lesson_id: process.env.M083_INTERACTIVE_LESSON_ID! }
    : JSON.parse(readFileSync('../.speech-data/m08-browser-fixture.json', 'utf8'));
});
async function login(page: Page, email: string) {
  await page.goto('/login'); await page.getByLabel('Email').fill(email);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  const [response] = await Promise.all([
    page.waitForResponse(response => response.url() === `${base}/auth/login` && response.request().method() === 'POST'),
    page.getByRole('button', { name: 'Sign in', exact: true }).click(),
  ]);
  expect(response.status()).toBe(200);
  const { user } = await response.json();
  expect(user.email === email).toBe(true);
  await expect(page).toHaveURL(/\/dashboard$/);
}
async function headers(page: Page) {
  return { Origin: new URL(page.url()).origin, 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === csrfName)!.value };
}

test('the designated admin retains draft access across Learn tabs and loses it on sign-out', async ({ page }) => {
  await login(page, fixture.admin);
  const navigation = page.getByRole('navigation', { name: 'Main navigation' });
  await expect(navigation.getByRole('link')).toHaveText(['Home', 'Learn', 'AI Tutor', 'Speak', 'Profile']);
  await navigation.getByRole('link', { name: 'Profile', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your profile' })).toBeVisible();
  const profile = await page.request.get(`${base}/auth/me`);
  expect(profile.status()).toBe(200);
  const { user } = await profile.json();
  expect(user.email === fixture.admin).toBe(true);
  expect(user.role).toBe('admin');
  expect(user.email_verified).toBe(true);

  const cookies = await page.context().cookies();
  const sessionName = process.env.M08_E2E_SESSION_COOKIE_NAME ?? 'fluentloop_m08_session';
  for (const [name, path, httpOnly] of [[sessionName, '/api/v1', true], [csrfName, '/', false]]) {
    const cookie = cookies.find(cookie => cookie.name === name);
    expect(cookie && { domain: cookie.domain, path: cookie.path, httpOnly: cookie.httpOnly, secure: cookie.secure, sameSite: cookie.sameSite })
      .toEqual({ domain: '127.0.0.1', path, httpOnly, secure: false, sameSite: 'Lax' });
  }

  await page.goto('/courses');
  const banner = page.getByRole('status', { name: 'Learning access' });
  await expect(banner).toContainText('Authorized draft preview');
  await page.reload();
  await expect(banner).toContainText('Authorized draft preview');
  const tabs = page.getByRole('navigation', { name: 'Learn sections' });
  for (const section of ['Grammar', 'Practice', 'Lessons']) {
    await tabs.getByRole('link', { name: section, exact: true }).click();
    await expect(tabs.getByRole('link', { name: section, exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(banner).toContainText('Authorized draft preview');
  }

  const courses = await page.request.get(`${base}/courses?level=A1`);
  expect(courses.status()).toBe(200);
  expect((await courses.json()).items.some((course: { draft_preview: boolean }) => course.draft_preview)).toBe(true);
  const lessonUrl = `${base}/lessons/${fixture.lesson_id}`;
  expect((await page.request.get(lessonUrl)).status()).toBe(200);
  const origin = new URL(page.url()).origin;
  expect((await page.request.post(`${base}/auth/logout`, { headers: { Origin: origin } })).status()).toBe(403);
  const accountMenu = page.locator('.account-menu:visible');
  await accountMenu.getByLabel('Account options').click();
  await accountMenu.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/login(?:\?|$)/);
  expect((await page.request.get(`${base}/auth/me`)).status()).toBe(401);
  expect((await page.request.get(lessonUrl)).status()).toBe(401);
  expect((await page.context().cookies()).some(cookie => [sessionName, csrfName].includes(cookie.name))).toBe(false);
  const session = cookies.find(cookie => cookie.name === sessionName)!;
  expect((await page.request.get(`${base}/auth/me`, {
    headers: { Cookie: `${sessionName}=${session.value}` },
  })).status()).toBe(401);
});

test('authorized preview shows actual availability and grammar actions on desktop and mobile', async ({ page }) => {
  await login(page, fixture.admin);
  await page.goto('/practice');
  await expect(page.getByRole('status', { name: 'Learning access' })).toContainText('Authorized draft preview');
  const catalog = await (await page.request.get(`${base}/learning/practice/catalog`)).json();
  expect(catalog.access_mode).toBe('draft_preview');
  const titles: Record<string, string> = { grammar: 'Grammar', sentence_building: 'Sentence building', listening: 'Listening', mistakes: 'Review mistakes' };
  for (const item of catalog.items) {
    const card = page.getByRole('article').filter({ has: page.getByRole('heading', { name: titles[item.category], exact: true }) });
    const button = card.getByRole('button', { name: 'Start practice' });
    if (item.available_exercises > 0) { await expect(button).toBeEnabled(); await expect(card).toContainText(`${item.available_exercises} authorized exercises available`); }
    else { await expect(button).toBeDisabled(); await expect(button).toHaveCSS('cursor', 'not-allowed'); }
  }
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
  await page.goto('/grammar');
  const grammar = page.getByRole('region', { name: 'Grammar practice' });
  await expect(grammar.getByRole('heading', { name: 'Common mistakes' })).toBeVisible();
  await grammar.getByRole('button', { name: 'Ask AI Tutor', exact: true }).click();
  await expect(page).toHaveURL(/\/ai-tutor\/[0-9a-f-]+$/);
});

test('ordinary learner sees an explanation and truly disabled buttons; foreign default cookies cannot grant preview', async ({ page }) => {
  await login(page, fixture.learner);
  const profile = await page.request.get(`${base}/auth/me`);
  expect(profile.status()).toBe(200);
  const { user } = await profile.json();
  expect(user.email === fixture.learner).toBe(true);
  expect(user.role).toBe('learner');
  expect((await page.request.get(`${base}/lessons/${fixture.lesson_id}`)).status()).toBe(404);
  await page.goto(`/learn/${fixture.lesson_id}`);
  await expect(page.getByText('Lesson not found.', { exact: true })).toBeVisible();
  await page.context().addCookies([{ name: 'fluentloop_session', value: 'untrusted-foreign-cookie', url: 'http://127.0.0.1' }]);
  await page.goto('/practice');
  await expect(page.getByRole('status', { name: 'Learning access' })).toContainText('Published content only');
  for (const button of await page.getByRole('button', { name: 'Start practice' }).all()) {
    await expect(button).toBeDisabled(); await expect(button).toHaveCSS('cursor', 'not-allowed');
  }
  await expect(page.getByText(/No published exercises are available at A1/).first()).toBeVisible();
  const denied = await page.request.post(`${base}/learning/practice/sessions`, { headers: await headers(page), data: { category: 'grammar' } });
  expect(denied.status()).toBe(409);
  await page.goto('/grammar');
  await expect(page.getByText('No published grammar topics are available at A1 yet.', { exact: true })).toBeVisible();
  expect((await (await page.request.get(`${base}/learning/access`)).json()).mode).toBe('published_only');
});

test('mixed answers, explicit errors, resume, idempotency, sign-in persistence and no SRS double count use real PostgreSQL', async ({ page }) => {
  test.setTimeout(180000); await login(page, fixture.admin);
  const before = await (await page.request.get(`${base}/review/progress`)).json();
  const preferences = await (await page.request.get(`${base}/users/me/preferences`)).json();
  const postHeaders = await headers(page);
  const active = await (await page.request.get(`${base}/learning/sessions?status=in_progress`)).json();
  for (const item of active.items) if (item.lesson_id === fixture.lesson_id && item.activity_key === 'lesson')
    expect((await page.request.post(`${base}/learning/sessions/${item.id}/abandon`, { headers: postHeaders })).ok()).toBeTruthy();
  await page.goto(`/learn/${fixture.lesson_id}`); await page.getByRole('button', { name: 'Start or continue lesson' }).click();
  await expect(page).toHaveURL(/\/learning\/sessions\//); await enterExercises(page); const url = page.url(); const sid = url.split('/').at(-1);
  const initialResponse = await page.request.get(`${base}/learning/sessions/${sid}`); const initial = await initialResponse.json();
  expect(initial.lesson_content_version).toBe('0.1.1'); expect(initial.exercises[0].options).toHaveLength(4);
  expect(JSON.stringify(initial)).not.toMatch(/accepted_orders|answer_pairs|accepted_answers|correct_option_id|text_fr/);
  await page.getByRole('radio', { name: 'es', exact: true }).check();
  let first: { url: string; data: unknown } | undefined;
  page.on('request', request => { if (!first && request.method() === 'POST' && request.url().endsWith('/answers')) first = { url: request.url(), data: request.postDataJSON() }; });
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Not quite.', exact: true })).toBeVisible();
  const replay = await page.request.post(first!.url, { headers: postHeaders, data: first!.data });
  expect((await replay.json()).idempotent_replay).toBe(true);
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByLabel('Your answer', { exact: true }).fill('es');
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Correct!', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /Save and exit/ }).click(); await page.goto(url); await page.reload();
  await expect(page.getByText('2 / 6 answered', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  for (const word of ['Je', 'suis', 'étudiant']) await page.getByLabel('Available words').getByRole('button', { name: word, exact: true }).click();
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  for (const [fr, en] of [['Je suis ici.', 'I am here.'], ['Tu es ici.', 'You are here.'], ['Elle est ici.', 'She is here.']]) await page.getByLabel(fr, { exact: true }).selectOption({ label: en });
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Load French audio' }).click(); await expect(page.getByLabel('French listening audio')).toBeVisible({ timeout: 60000 });
  await page.getByRole('radio', { name: 'She is here.', exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  const written = page.getByLabel('Your answer', { exact: true });
  await written.fill('Je suis tudiante.');
  await written.evaluate((input: HTMLInputElement) => input.setSelectionRange(8, 8));
  await page.getByRole('button', { name: 'Insert é', exact: true }).click();
  await expect(written).toHaveValue('Je suis étudiante.');
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await page.getByRole('button', { name: 'Continue to completion' }).click();
  await page.getByRole('button', { name: 'Complete lesson', exact: true }).click();
  await expect(page).toHaveURL(/\/learning\/results\//);
  const saved = await (await page.request.get(`${base}/learning/sessions/${sid}`)).json();
  expect(saved.answered_exercises).toBe(6); expect(saved.percentage).toBe(83.33);
  expect(saved.exercises[0].feedback.is_correct).toBe(false);
  expect(saved.exercises[5].submitted_answer.text_answer).toBe('Je suis étudiante.');
  const recommendations = await (await page.request.get(`${base}/study/recommendations`)).json();
  expect(recommendations.some((r: { evidence_attempt_ids: string[] }) => r.evidence_attempt_ids.length > 0)).toBe(true);
  const after = await (await page.request.get(`${base}/review/progress`)).json();
  expect(after.reviews_completed).toBe(before.reviews_completed);
  expect((await (await page.request.get(`${base}/users/me/preferences`)).json()).current_level).toBe(preferences.current_level);
  const planResponse = await page.request.post(`${base}/study/today/generate`, { headers: postHeaders, data: { request_id: crypto.randomUUID() } });
  expect(planResponse.ok()).toBe(true); const plan = await planResponse.json();
  expect(plan.cefr_level).toBe('A1');
  expect((await (await page.request.get(`${base}/study/today`)).json()).id).toBe(plan.id);
  await page.goto('/dashboard');
  const accountMenu = page.locator('.account-menu:visible');
  await accountMenu.getByLabel('Account options').click();
  await accountMenu.getByRole('button', { name: 'Sign out' }).click();
  await login(page, fixture.admin); await page.goto(`/learning/results/${sid}`);
  await expect(page.getByText('83.33%', { exact: true })).toBeVisible();
  expect((await (await page.request.get(`${base}/study/today`)).json()).id).toBe(plan.id);
  const progressBefore = await (await page.request.get(`${base}/learning/progress/lessons/${fixture.lesson_id}`)).json();
  await page.getByRole('link', { name: 'Review mistakes', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Mistake review' })).toBeVisible();
  await page.getByRole('button', { name: 'Practice this mistake', exact: true }).first().click();
  await expect(page).toHaveURL(/\/learning\/sessions\//);
  await page.getByRole('radio', { name: 'suis', exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Correct!', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to completion', exact: true }).click();
  await page.getByRole('button', { name: 'Complete practice', exact: true }).click();
  await expect(page.getByText('A1 practice complete', { exact: true })).toBeVisible();
  expect((await (await page.request.get(`${base}/learning/progress/lessons/${fixture.lesson_id}`)).json()).completion_count).toBe(progressBefore.completion_count);
  const historical = await (await page.request.get(`${base}/learning/sessions/${sid}`)).json();
  expect(historical.exercises[0].feedback.is_correct).toBe(false);
  await page.getByRole('link', { name: 'Continue learning', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/courses\\?level=a1&lesson=${fixture.lesson_id}`));
  await expect(page.locator(`[id="lesson-${fixture.lesson_id}"]`)).toHaveAttribute('aria-current', 'location');
});
