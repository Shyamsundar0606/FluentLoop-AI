import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import type { AssessmentDefinition } from "../lib/assessments";
import type { LearningSession } from "../lib/learning";

test.use({ trace: "off" });
test.skip(process.env.M10_REAL_E2E !== "1", "Requires the explicitly disposable M10 demo and WSL cluster.");
const api = "http://127.0.0.1:8012/api/v1";

function frozenAnswers(sessionId: string) {
  // Trusted test-side access only. The learner API must never return these keys.
  const code = `
import json,sys
from pathlib import Path
from uuid import UUID
import psycopg
root=Path.cwd().parent
s=json.loads((root/'.publication-private/integration-wsl/state.json').read_text())
assert s['postgres_port']==55432 and s['username']=='fluentloop_test'
options=dict(host='127.0.0.1',port=55432,user=s['username'],password=s['password'],options='-c default_transaction_read_only=on')
with psycopg.connect(dbname='postgres',**options) as db:
    names=db.execute("SELECT datname FROM pg_database WHERE datname LIKE 'fluentloop_m08_3_test_%'").fetchall()
matches=[]
for (name,) in names:
    with psycopg.connect(dbname=name,**options) as db:
        rows=db.execute('SELECT id, exercise_snapshot FROM learning_session_exercises WHERE learning_session_id=%s',(UUID(sys.argv[1]),)).fetchall()
        if rows: matches.append(rows)
assert len(matches)==1,'The saved session must resolve to exactly one disposable demo database'
rows=matches[0]
print(json.dumps({str(identifier):snapshot for identifier,snapshot in rows}))
`;
  return JSON.parse(execFileSync(resolve("../.venv312/Scripts/python.exe"), ["-c", code, sessionId], { encoding: "utf8" })) as Record<string, {
    correct_option_id?: string; accepted_answers?: string[]; answer_pairs?: Record<string, string>;
  }>;
}

test("five real assessment categories persist, resume and deny ordinary draft access", async ({ page, browser }) => {
  test.setTimeout(240_000);
  const fixture = JSON.parse(readFileSync(resolve("../.publication-private/m08/m09-manual-fixture.json"), "utf8")) as {
    email: string; password: string; learner_email: string;
  };
  await page.goto("/login");
  await page.getByLabel("Email").fill(fixture.email);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const catalog = await (await page.request.get(`${api}/learning/assessments`)).json() as { items: AssessmentDefinition[] };
  expect(new Set(catalog.items.map(item => item.skill)).size).toBe(5);
  for (const skill of ["grammar", "vocabulary", "reading", "listening"] as const) {
    const definition = catalog.items.find(item => item.skill === skill &&
      (!['grammar', 'listening'].includes(skill) || item.title.startsWith("Être:")))!;
    expect(definition).toBeTruthy();
    await page.goto("/assessments");
    const card = page.getByRole("article").filter({ has: page.getByRole("heading", { name: definition.title, exact: true }) })
      .filter({ has: page.getByText(`${skill} · A1`, { exact: true }) });
    await card.getByRole("button", { name: `Start or resume ${skill} assessment` }).click();
    await expect(page).toHaveURL(/\/learning\/sessions\//);
    const id = page.url().split("/").at(-1)!;
    const response = await page.request.get(`${api}/learning/sessions/${id}`);
    const session = await response.json() as LearningSession;
    expect(JSON.stringify(session)).not.toMatch(/correct_option_id|accepted_answers|answer_pairs/);
    const keys = frozenAnswers(id);
    if (skill === "reading") await expect(page.getByRole("region", { name: "Assessment task" })).toContainText("J'habite à Lyon");
    for (const exercise of session.exercises) {
      const key = keys[exercise.id];
      if (exercise.type === "listening") {
        await page.getByRole("button", { name: "Load French audio", exact: true }).click();
        await expect(page.locator("audio")).toHaveAttribute("src", /blob:/, { timeout: 90_000 });
      }
      if (key.correct_option_id) {
        const option = exercise.options.find(item => item.id === key.correct_option_id)!;
        await page.getByRole("radio", { name: option.text, exact: true }).check();
      } else if (key.accepted_answers) {
        await page.getByLabel("Your answer", { exact: true }).fill(key.accepted_answers[0]);
      } else if (key.answer_pairs) {
        for (const [left, right] of Object.entries(key.answer_pairs)) {
          const label = exercise.left_items!.find(item => item.id === left)!.text;
          await page.getByLabel(label, { exact: true }).selectOption(right);
        }
      } else throw new Error("Unexpected assessment fixture format");
      await page.getByRole("button", { name: "Submit answer", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Correct!", exact: true })).toBeVisible();
      if (skill === "reading" && exercise.exercise_order === 1) {
        await page.reload();
        await expect(page.getByRole("heading", { name: "Correct!", exact: true })).toBeVisible();
      }
      await page.getByRole("button", { name: /^Continue(?: to completion)?$/, exact: true }).click();
    }
    await page.getByRole("button", { name: "Complete assessment", exact: true }).click();
    await expect(page.getByRole("region", { name: "Saved results" })).toContainText("100%");
  }
  const writing = catalog.items.find(item => item.skill === "writing")!;
  await page.goto(`/assessments/writing/${writing.lesson_id}`);
  await page.getByLabel("Your French response").fill("Je m'appelle Lina. J'habite à Lyon. J'aime lire.");
  await page.getByRole("button", { name: "Save writing", exact: true }).click();
  await expect(page).toHaveURL(/submission=/);
  const writingId = new URL(page.url()).searchParams.get("submission")!;
  await page.reload();
  await expect(page.getByRole("heading", { name: "Your saved original response" })).toBeVisible();
  await page.getByRole("button", { name: "Request optional AI feedback" }).click();
  await expect(page.getByRole("heading", { name: "Advisory AI feedback" })).toBeVisible({ timeout: 90_000 });
  await page.goto("/progress");
  await expect(page.getByRole("region", { name: "Assessment evidence" })).toContainText("1 saved submissions");
  const other = await browser.newContext();
  try {
    const learner = await other.newPage();
    await learner.goto("/login");
    await learner.getByLabel("Email").fill(fixture.learner_email);
    await learner.locator('input[autocomplete="current-password"]').fill(fixture.password);
    await learner.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(learner).toHaveURL(/\/dashboard$/);
    expect((await (await learner.request.get(`${api}/learning/assessments`)).json()).items).toEqual([]);
    expect((await learner.request.get(`${api}/learning/assessments/writing/${writingId}`)).status()).toBe(404);
  } finally { await other.close(); }
});
