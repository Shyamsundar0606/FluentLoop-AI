import { test, expect } from '@playwright/test';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

const capture = resolve('../.speech-data/m08_1/conversation-capture.wav');
test.use({ permissions: ['microphone'], launchOptions: { args: [
  '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
  `--use-file-for-fake-audio-capture=${capture}`,
] } });

test('real recorded WebM, Base ASR, Ollama, Piper replay and persisted speech history', async ({ page }) => {
  test.skip(process.env.M08_SPEECH_LIVE !== '1' || !existsSync(capture), 'Requires the isolated real worker/models and generated synthetic French input.');
  test.setTimeout(180000);
  const fixture = JSON.parse(readFileSync('../.speech-data/m08-browser-fixture.json', 'utf8'));
  await page.goto('/login'); await page.getByLabel('Email').fill(fixture.admin);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto(`/learn/${fixture.lesson_id}`);
  await page.getByRole('button', { name: 'Practice speaking', exact: true }).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\//); const url = page.url(); const sid = url.split('/').at(-1);
  await page.getByRole('button', { name: 'Record French', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop recording', exact: true })).toBeVisible();
  await page.waitForTimeout(6000); // Capture actual synthetic French audio, not an empty fake device.
  await page.getByRole('button', { name: 'Stop recording', exact: true }).click();
  const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/speech/sessions/${sid}/turns`));
  await page.getByRole('button', { name: 'Send recording', exact: true }).click();
  const result = await (await response).json();
  expect(result.transcription.model).toBe('base');
  expect(result.transcription.codec).toBe('opus');
  expect(result.transcription_status).toBe('transcribed');
  expect(result.transcript).toMatch(/je suis/i);
  expect(result.tutor.cefr_level).toBe('A1'); expect(result.tutor_audio.status).toBe('ready');
  await expect(page.getByRole('button', { name: 'Play tutor audio', exact: true }).last()).toBeVisible();
  await page.getByRole('button', { name: 'Play tutor audio', exact: true }).last().click();
  await page.reload();
  const saved = await (await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}`)).json();
  expect(saved.turns.some((turn: { id: string }) => turn.id === result.id)).toBe(true);
  await page.goto('/voice-practice/history'); await expect(page.getByRole('heading', { name: 'Practice activity' })).toBeVisible();
});

test('genuine Base uncertainty remains editable and requires explicit confirmation before tutor submission', async ({ page }) => {
  const uncertain = resolve('../.speech-data/m08_1/uncertain.wav');
  test.skip(process.env.M08_SPEECH_LIVE !== '1' || !existsSync(uncertain), 'Requires the naturally uncertain synthetic sample from real Base inference.');
  test.setTimeout(180000);
  const fixture = JSON.parse(readFileSync('../.speech-data/m08-browser-fixture.json', 'utf8'));
  await page.goto('/login'); await page.getByLabel('Email').fill(fixture.admin);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto(`/learn/${fixture.lesson_id}`); await page.getByRole('button', { name: 'Practice speaking', exact: true }).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\//); const sid = page.url().split('/').at(-1);
  const cookie = process.env.PLAYWRIGHT_CSRF_COOKIE_NAME ?? 'fluentloop_csrf';
  const csrf = (await page.context().cookies()).find(c => c.name === cookie)!.value;
  const sourceResponse = await page.request.post(`${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}/turns`, {
    headers: { Origin: new URL(page.url()).origin, 'X-CSRF-Token': csrf },
    multipart: { request_id: crypto.randomUUID(), retain_audio: 'false', audio: { name: 'synthetic-name.wav', mimeType: 'audio/wav', buffer: readFileSync(uncertain) } },
  });
  expect(sourceResponse.ok()).toBe(true); const source = await sourceResponse.json();
  expect(source.transcription.model).toBe('base'); expect(source.transcription_status).toBe('uncertain');
  expect(source.tutor).toBeNull();
  let textPosts = 0; page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/text')) textPosts++; });
  await page.reload(); await expect(page.getByLabel('Corrected sentence')).toHaveValue(source.transcript);
  expect(textPosts).toBe(0);
  await page.getByLabel('Corrected sentence').fill("Je m'appelle Camille.");
  const confirmation = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/speech/sessions/${sid}/text`));
  await page.getByRole('button', { name: 'Confirm and send', exact: true }).click();
  const confirmed = await (await confirmation).json();
  expect(confirmed.transcription_status).toBe('user_confirmed'); expect(confirmed.review.edited).toBe(true);
  expect(confirmed.review.original_text).toBe(source.transcript); expect(textPosts).toBe(1);
  await expect(page.getByText('Edited transcript', { exact: true })).toBeVisible();
  const history = await (await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}`)).json();
  expect(history.turns.find((turn: { id: string }) => turn.id === source.id).transcript).toBe(source.transcript);
});
