import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { mkdirSync } from "node:fs";

test.use({
  permissions: ["microphone"],
  launchOptions: {
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
    ],
  },
});

test.beforeEach(async ({ page }) => {
  test.skip(
    process.env.SPEECH_E2E_REAL_API !== "1",
    "Requires the isolated M06 API with fake inference",
  );
  await page.goto("/login");
  await page.getByLabel("Email").fill("ai-browser@example.com");
  await page
    .locator('input[autocomplete="current-password"]')
    .fill("IsolatedBrowserTest2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("record-stop-review-submit, saved transcript, replay, history and text fallback", async ({
  page,
}) => {
  await page.goto("/voice-practice");
  await expect(
    page.getByRole("heading", {
      name: "Practice Speaking French",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  await expect(
    page
      .getByRole("region", { name: "Microphone recording" })
      .getByRole("status"),
  ).toHaveText("Microphone off");
  await page.getByRole("button", { name: "Record French" }).click();
  await expect(page.getByRole("status")).toContainText("Recording");
  await page.waitForTimeout(600);
  await page.getByText("Recording options & privacy", { exact: true }).click();
  await page.getByRole("button", { name: "Pause recording" }).click();
  await expect(page.getByRole("status")).toContainText("paused");
  await page.getByRole("button", { name: "Resume recording" }).click();
  await page.waitForTimeout(300);
  await page.getByRole("button", { name: "Stop recording" }).click();
  await expect(page.getByLabel("Review your recording")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Microphone off");
  await page.getByRole("button", { name: "Send recording" }).click();
  await expect(
    page.getByRole("list", { name: "Voice conversation turns" }),
  ).toContainText("Bonjour, je voudrais une baguette.");
  await expect(
    page.getByRole("button", { name: "Play tutor audio" }),
  ).toBeVisible();
  const audio = page.getByLabel("Play or replay tutor voice");
  await expect
    .poll(() => audio.evaluate((el: HTMLAudioElement) => el.readyState))
    .toBeGreaterThan(0);
  await page.getByRole("button", { name: "Play tutor audio" }).click();
  await expect
    .poll(() => audio.evaluate((el: HTMLAudioElement) => el.currentTime))
    .toBeGreaterThan(0);
  const saved = page.url();
  await page.reload();
  await expect(
    page.getByRole("list", { name: "Voice conversation turns" }),
  ).toContainText("Bonjour");
  await page
    .getByText("Text fallback & conversation options", { exact: true })
    .click();
  await page.getByLabel("Text fallback").fill("Bonjour, encore une question.");
  await page.getByRole("button", { name: "Send text instead" }).click();
  await expect(
    page.getByRole("list", { name: "Voice conversation turns" }),
  ).toContainText("Bonjour, encore une question.");
  const ordered = page.getByRole("list", { name: "Voice conversation turns" }).locator(".voice-chat-turn");
  await expect(ordered).toHaveCount(2);
  await expect(ordered.nth(0)).toContainText("Bonjour, je voudrais une baguette.");
  await expect(ordered.nth(1)).toContainText("Bonjour, encore une question.");
  await page.goto("/voice-practice/history");
  await page
    .getByRole("link", { name: /French voice practice/ })
    .first()
    .click();
  await expect(page).toHaveURL(saved);
});

test("permission failure has text fallback; unmount/cancel leaves microphone off", async ({
  page,
}) => {
  await page.goto("/voice-practice");
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  await page.evaluate(() => {
    navigator.mediaDevices.getUserMedia = () =>
      Promise.reject(new DOMException("Denied", "NotAllowedError"));
  });
  await page.getByRole("button", { name: "Record French" }).click();
  await expect(page.locator('p[role="alert"]')).toContainText(
    "permission denied",
  );
  await page
    .getByText("Text fallback & conversation options", { exact: true })
    .click();
  await page.getByLabel("Text fallback").fill("Bonjour, comment allez-vous ?");
  await page.getByRole("button", { name: "Send text instead" }).click();
  await expect(
    page.getByRole("list", { name: "Voice conversation turns" }),
  ).toContainText("comment allez-vous");
});

test("private replay consent, playback options and deletion remain accessible", async ({
  page,
}) => {
  await page.goto("/voice-practice");
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  await page.getByRole("button", { name: "Record French" }).click();
  await page.waitForTimeout(700);
  await page.getByRole("button", { name: "Stop recording" }).click();
  await page.getByText("Recording options & privacy", { exact: true }).click();
  const consent = page.getByLabel(/Keep this recording privately/);
  await expect(consent).not.toBeChecked();
  await consent.check();
  await page.getByRole("button", { name: "Send recording" }).click();
  const turns = page.getByRole("list", { name: "Voice conversation turns" });
  await turns.getByText("Recognition details", {exact: true}).click();
  const ownAudio = turns
    .locator(".my-3")
    .filter({ has: page.getByRole("button", { name: "Play your recording" }) })
    .first();
  await expect(
    ownAudio.getByRole("button", { name: "Play your recording" }),
  ).toBeVisible();
  await ownAudio.getByText("Audio options & privacy", { exact: true }).click();
  await ownAudio.getByLabel("Playback speed").selectOption("0.75");
  expect(
    await ownAudio
      .locator("audio")
      .evaluate((el: HTMLAudioElement) => el.playbackRate),
  ).toBe(0.75);
  await ownAudio.getByRole("button", { name: "Delete this audio" }).click();
  await expect(
    turns.getByRole("button", { name: "Play your recording" }),
  ).toHaveCount(0);
  await expect(
    turns.getByRole("button", { name: "Play tutor audio" }),
  ).toBeVisible();
});

test("uncertain recognition requires review and explicit text submission", async ({
  page,
}) => {
  let textPosts = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/text"))
      textPosts++;
  });
  await page.goto("/voice-practice");
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\/[0-9a-f-]+$/);
  const sid = page.url().split("/").pop();
  const csrf = (await page.context().cookies()).find(
    (c) => c.name === "fluentloop_csrf",
  )!.value;
  const response = await page.request.post(
    `${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}/turns`,
    {
      headers: { Origin: new URL(page.url()).origin, "X-CSRF-Token": csrf },
      multipart: {
        request_id: crypto.randomUUID(),
        retain_audio: "true",
        audio: {
          name: "human.ogg",
          mimeType: "audio/ogg",
          buffer: readFileSync(
            "../backend/tests/fixtures/speech/fr-bonjour.ogg",
          ),
        },
      },
    },
  );
  expect(response.ok()).toBeTruthy();
  const source = await response.json();
  await page.reload();
  await expect(page.getByText("Check what we heard and correct any mistakes.")).toBeVisible();
  await expect(page.getByRole("button", {name: "Confirm and send", exact: true})).toBeVisible();
  await expect(page.getByLabel("Corrected sentence")).toHaveValue(
    "Bonjour, Zamapel, Xiaomi, Zabite, Paris.",
  );
  await expect(page.getByLabel("Corrected sentence")).toBeFocused();
  expect(textPosts).toBe(0);
  if (process.env.UI_SCREENSHOTS === "1") {
    mkdirSync("../docs/verification/frontend-redesign", { recursive: true });
    await page.screenshot({
      path: "../docs/verification/frontend-redesign/transcript-review.png",
      fullPage: false,
    });
  }
  await page
    .getByLabel("Corrected sentence")
    .fill("Bonjour, je m'appelle Camille. J'habite à Paris.");
  await page.getByRole("button", {name: "Confirm and send", exact: true}).click({clickCount: 2});
  await expect(page.getByText("Edited transcript", {exact: true})).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Play tutor audio" }),
  ).toBeVisible();
  expect(textPosts).toBe(1);
  await page.reload();
  const thread = page.getByRole("list", {name: "Voice conversation turns"});
  await expect(thread.getByText("Edited transcript", {exact: true})).toBeVisible();
  await expect(thread.locator(".voice-chat-turn")).toHaveCount(1);
  await expect(thread.getByText("Bonjour, je m'appelle Camille. J'habite \u00e0 Paris.", {exact: true})).toBeVisible();
  await expect(thread.getByText("Bonjour, Zamapel, Xiaomi, Zabite, Paris.", {exact: true})).toHaveCount(0);
  if (process.env.UI_SCREENSHOTS === "1") {
    mkdirSync("../docs/verification/voice-ux", {recursive: true});
    for (const width of [390, 1440]) {
      await page.setViewportSize({width, height: 900});
      await thread.scrollIntoViewIfNeeded();
      await page.screenshot({path: `../docs/verification/voice-ux/confirmed-${width}.png`});
    }
  }
  await thread.getByText("Recognition details", {exact: true}).click();
  await expect(thread.locator("details[open]")).toContainText("Bonjour, Zamapel, Xiaomi, Zabite, Paris.");
  await expect(thread.getByRole("button", {name: "Play your recording", exact: true})).toBeVisible();
  const saved = await page.request.get(
    `${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}`,
  );
  const turns = (await saved.json()).turns;
  expect(turns[0].transcript).toBe("Bonjour, Zamapel, Xiaomi, Zabite, Paris.");
  expect(turns[1].review.source_turn_id).toBe(source.id);
  expect(turns[1].review.edited).toBe(true);
  expect(turns[1].review.confirmed_text).toBe(
    "Bonjour, je m'appelle Camille. J'habite à Paris.",
  );
});

test("pronunciation reference, recording, unavailable acoustic score and history", async ({
  page,
}) => {
  await page.goto("/voice-practice/pronunciation");
  await page.locator("main li a").first().click();
  await expect(
    page.getByText("Draft preview · unreviewed target"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Prepare French audio" }).click();
  await expect(
    page.getByRole("button", { name: "Listen to sentence" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Record French" }).click();
  await page.waitForTimeout(600);
  await page.getByRole("button", { name: "Stop recording" }).click();
  await page.getByRole("button", { name: "Send recording" }).click();
  await expect(
    page.getByText("Acoustic assessment: not available").first(),
  ).toBeVisible();
  await expect(page.getByText(/Recognized: Bonjour/).first()).toBeVisible();
  await page.goto("/voice-practice/history");
  await expect(
    page.getByRole("heading", { name: "Practice activity" }),
  ).toBeVisible();
  await expect(
    page.getByText(/attempts · acoustic scoring unavailable/),
  ).toBeVisible();
});

test("cross-user speech session denial and no draft targets for ordinary learner", async ({
  page,
}) => {
  await page.goto("/voice-practice");
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\/[0-9a-f-]+$/);
  const saved = page.url();
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.getByLabel("Email").fill("ai-other@example.com");
  await page
    .locator('input[autocomplete="current-password"]')
    .fill("IsolatedBrowserTest2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto(saved);
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "Speech session not found.",
  );
  await page.goto("/voice-practice/pronunciation");
  await expect(
    page.getByText(/No accessible pronunciation targets/),
  ).toBeVisible();
});

test("cancel and route unmount release every microphone track", async ({
  page,
}) => {
  await page.goto("/voice-practice");
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\/[0-9a-f-]+$/);
  await page.evaluate(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(
      navigator.mediaDevices,
    );
    const tracked = window as unknown as {
      voiceTestTracks: MediaStreamTrack[];
    };
    tracked.voiceTestTracks = [];
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      const stream = await original(constraints);
      tracked.voiceTestTracks.push(...stream.getTracks());
      return stream;
    };
  });
  await page.getByRole("button", { name: "Record French" }).click();
  await expect(
    page.getByRole("button", { name: "Stop recording" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Cancel recording" }).click();
  await expect(page.getByRole("status")).toHaveText("Microphone off");
  expect(
    await page.evaluate(() =>
      (
        window as unknown as { voiceTestTracks: MediaStreamTrack[] }
      ).voiceTestTracks.every((t) => t.readyState === "ended"),
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Record French" }).click();
  await expect(
    page.getByRole("button", { name: "Stop recording" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "AI Tutor", exact: true }).click();
  await expect(page).toHaveURL(/\/ai-tutor$/);
  await expect
    .poll(() =>
      page.evaluate(() =>
        (
          window as unknown as { voiceTestTracks: MediaStreamTrack[] }
        ).voiceTestTracks.every((t) => t.readyState === "ended"),
      ),
    )
    .toBe(true);
});

test("mobile review can record again and confirm unchanged recognition honestly", async ({ page }) => {
  await page.setViewportSize({width: 390, height: 844});
  let textPosts = 0;
  page.on('request', request => { if (request.method() === 'POST' && /\/speech\/sessions\/[^/]+\/text$/.test(request.url())) textPosts++; });
  await page.goto('/voice-practice');
  await page.getByRole('button', {name: 'Start Voice Conversation'}).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\/[0-9a-f-]+$/);
  const sid = page.url().split('/').pop();
  const csrf = (await page.context().cookies()).find(c => c.name === 'fluentloop_csrf')!.value;
  const sourceResponse = await page.request.post(`${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}/turns`, {
    headers: {Origin: new URL(page.url()).origin, 'X-CSRF-Token': csrf},
    multipart: {request_id: crypto.randomUUID(), retain_audio: 'false', audio: {name: 'human.ogg', mimeType: 'audio/ogg', buffer: readFileSync('../backend/tests/fixtures/speech/fr-bonjour.ogg')}}
  });
  expect(sourceResponse.ok()).toBeTruthy();
  const source = await sourceResponse.json();
  await page.reload();
  await expect(page.getByLabel('Corrected sentence')).toBeFocused();
  await page.getByLabel('Corrected sentence').fill('My unsent edit');
  await page.getByRole('button', {name: 'Record again', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Stop recording'})).toBeVisible();
  expect(textPosts).toBe(0);
  await page.getByRole('button', {name: 'Cancel recording'}).click();
  await expect(page.getByLabel('Corrected sentence')).toHaveCount(0);
  const thread = page.getByRole('list', {name: 'Voice conversation turns'});
  await thread.getByText('Recognition details', {exact: true}).click();
  await thread.getByRole('button', {name: 'Review this recording'}).click();
  await expect(page.getByLabel('Corrected sentence')).toHaveValue(source.transcript);
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({width, height: 900});
    await page.getByLabel('Corrected sentence').focus();
    await expect(page.getByRole('button', {name: 'Confirm and send', exact: true})).toBeInViewport();
    const mic = page.getByRole('button', {name: 'Record French', exact: true});
    await expect(mic).toBeInViewport();
    const box = await mic.boundingBox();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (process.env.UI_SCREENSHOTS === '1') {
      mkdirSync('../docs/verification/voice-ux', {recursive:true});
      await page.screenshot({path:`../docs/verification/voice-ux/review-${width}.png`});
    }
  }
  await page.getByRole('button', {name:'Confirm and send', exact:true}).click();
  await expect(thread.getByRole('article', {name:'Tutor reply'})).toHaveCount(1);
  await expect(thread.getByText('Edited transcript', {exact:true})).toHaveCount(0);
  expect(textPosts).toBe(1);
  const saved = await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/speech/sessions/${sid}`);
  const turns = (await saved.json()).turns;
  expect(turns).toHaveLength(2);
  expect(turns[0].transcript).toBe(source.transcript);
  expect(turns[1].review.edited).toBe(false);
  expect(turns[1].review.confirmed_text).toBe(source.transcript);
});
