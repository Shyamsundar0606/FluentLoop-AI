import { expect, test } from "@playwright/test";

test("author saves a real-version checkpoint, edits a draft and opens the comparison report (mock API)", async ({ page }) => {
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
  const origin = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin;
  const slug = "draft-reading";
  const sectionId = "a1111111-1111-4111-8111-111111111111";
  const oldId = "b2222222-2222-4222-8222-222222222222";
  const newId = "c3333333-3333-4333-8333-333333333333";
  const oldDigest = "a".repeat(64);
  let edited = false;
  let stored = false;
  await page.route(`${api}/**`, async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const headers = { "access-control-allow-origin": origin, "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,POST,OPTIONS", "access-control-allow-headers": "content-type,x-csrf-token" };
    if (request.method() === "OPTIONS") { await route.fulfill({ status: 200, headers }); return; }
    const old = { id: oldId, version: "0.1.0", digest: oldDigest, created_at: "2026-11-15T12:00:00Z" };
    const current = { id: newId, version: "0.1.1", digest: "b".repeat(64), created_at: "2026-11-15T12:01:00Z" };
    let body: unknown = {};
    if (path.endsWith("/auth/me")) body = { user: { id: "author", email: "author@example.test", role: "admin",
      email_verified: true, display_name: "Author", native_language: "English", timezone: "UTC", onboarding_completed: true,
      preferences: { current_level: "a1", daily_study_minutes: 15, theme: "light" } } };
    else if (path.endsWith("/content-review/queue")) body = { can_author: true, items: [{ slug, title: "Draft reading", version: "0.1.0", outstanding: [] }] };
    else if (path.endsWith("/revisions")) {
      if (request.method() === "POST") { stored = true; body = old; }
      else body = { items: edited ? [current, old] : stored ? [old] : [], next_offset: null };
    } else if (path.endsWith("/sections")) {
      expect(request.postDataJSON()).toEqual({ expected_digest: oldDigest, next_version: "0.1.1", section_id: sectionId, body_content: "Bonjour ! Bonne lecture !" });
      edited = true; body = current;
    } else if (path.endsWith("/compare")) body = { before: old, after: current, total_changes: 1,
      changes: [{ path: "lessons[0].sections[0].body_content", before: "Bonjour !", after: "Bonjour ! Bonne lecture !", before_exists: true, after_exists: true }] };
    else if (path.endsWith(`/content-review/${slug}`)) body = { can_author: true, digest: edited ? current.digest : oldDigest,
      categories: [], technical_issues: [], history: [], readiness: { outstanding: ["linguistic_accuracy", "phonetics", "pedagogy", "answer_keys", "licensing"], complete: false, independent_licensing: false },
      content: { version: edited ? "0.1.1" : "0.1.0", title: "Draft reading", lessons: [{ slug: "reading", title: "Reading lesson", exercises: [],
        sections: [{ id: sectionId, title: "Reading task", body_content: edited ? "Bonjour ! Bonne lecture !" : "Bonjour !" }] }] } };
    await route.fulfill({ json: body, headers });
  });
  await page.goto("/profile/curriculum-review");
  await page.getByRole("button", { name: "Draft reading · 0.1.0" }).click();
  await expect(page.getByText("No historical packet versions have been saved yet.")).toBeVisible();
  await page.getByRole("button", { name: "Save current packet version" }).click();
  await page.getByText("Edit a draft section", { exact: true }).click();
  await page.getByLabel("Section text", { exact: true }).fill("Bonjour ! Bonne lecture !");
  await page.getByLabel("New content version", { exact: true }).fill("0.1.1");
  await page.getByRole("button", { name: "Save draft revision" }).click();
  await expect(page.getByText(/Version 0.1.1/)).toBeVisible();
  await page.getByRole("button", { name: "Compare stored versions" }).click();
  await expect(page.getByRole("region", { name: "Stored version changes" })).toContainText("Bonjour ! Bonne lecture !");
  await expect(page.getByText("Independent licensing evidence is outstanding.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save review decision" })).toHaveCount(0);
});

test("staff edits exercise keys while preserving stable identifiers (mock API)", async ({ page }) => {
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
  const origin = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin;
  const exerciseId = "11111111-1111-4111-8111-111111111111";
  const optionId = "22222222-2222-4222-8222-222222222222";
  let edited = false;
  await page.route(`${api}/**`, async route => {
    const req = route.request(), path = new URL(req.url()).pathname;
    const headers = { "access-control-allow-origin": origin, "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,POST,OPTIONS", "access-control-allow-headers": "content-type,x-csrf-token" };
    if (req.method() === "OPTIONS") { await route.fulfill({ status: 200, headers }); return; }
    let body: unknown = {};
    if (path.endsWith("/auth/me")) body = { user: { id: "author", email: "author@example.test", role: "admin",
      email_verified: true, display_name: "Author", onboarding_completed: true, preferences: { current_level: "a1", theme: "light" } } };
    else if (path.endsWith("/queue")) body = { can_author: true, items: [{ slug: "draft", title: "Draft", version: edited ? "0.1.1" : "0.1.0" }] };
    else if (path.endsWith("/revisions")) body = { items: [], next_offset: null };
    else if (path.endsWith("/exercises")) {
      const submitted = req.postDataJSON();
      expect(submitted.exercise_id).toBe(exerciseId);
      expect(submitted.options[0].id).toBe(optionId);
      expect(submitted.options[0].is_correct).toBe(false);
      expect(submitted.options[1].is_correct).toBe(true);
      expect(submitted.next_version).toBe("0.1.1");
      expect(submitted.expected_digest).toBe("a".repeat(64));
      edited = true; body = { version: "0.1.1" };
    } else if (path.endsWith("/content-review/draft")) body = { can_author: true, digest: "a".repeat(64),
      categories: [], technical_issues: [], history: [], readiness: { outstanding: [], complete: false, independent_licensing: false },
      content: { title: "Draft", version: edited ? "0.1.1" : "0.1.0", lessons: [{ slug: "lesson", title: "Lesson",
        description: "Draft description", estimated_minutes: 10, sections: [], exercises: [{ id: exerciseId, type: "multiple_choice",
          prompt: "Choose suis", instructions: "Choose one answer.", feedback: "Use suis with je.", data: {},
          options: [{ id: optionId, option_text: "suis", is_correct: true },
            { id: "33333333-3333-4333-8333-333333333333", option_text: "es", is_correct: false }] }] }] } };
    await route.fulfill({ json: body, headers });
  });
  await page.goto("/profile/curriculum-review");
  await page.getByRole("button", { name: "Draft · 0.1.0" }).click();
  await page.getByText("Edit lesson details or exercise definition", { exact: true }).click();
  await page.getByLabel("Draft item", { exact: true }).selectOption(exerciseId);
  const editor = page.getByLabel("Selected draft fields", { exact: true });
  const fields = JSON.parse(await editor.inputValue());
  fields.options[0].is_correct = false;
  fields.options[1].is_correct = true;
  await editor.fill(JSON.stringify(fields));
  await page.getByLabel("Structured content version", { exact: true }).fill("0.1.1");
  await page.getByRole("button", { name: "Save structured draft revision" }).click();
  await expect(page.getByText(/Version 0.1.1/)).toBeVisible();
});

test("staff edits an exclusive vocabulary resource and versioned course provenance (mock API)", async ({ page }) => {
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
  const origin = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin;
  const id = "44444444-4444-4444-8444-444444444444";
  let version = "0.1.0";
  await page.route(`${api}/**`, async route => {
    const req = route.request(), path = new URL(req.url()).pathname;
    const headers = { "access-control-allow-origin":origin, "access-control-allow-credentials":"true",
      "access-control-allow-methods":"GET,POST,OPTIONS", "access-control-allow-headers":"content-type,x-csrf-token" };
    if (req.method()==="OPTIONS") { await route.fulfill({ status:200, headers }); return; }
    let body: unknown = {};
    if (path.endsWith("/auth/me")) body = { user:{ id:"author", email:"author@example.test", role:"admin", email_verified:true,
      display_name:"Author", onboarding_completed:true, preferences:{ current_level:"a1", theme:"light" } } };
    else if (path.endsWith("/queue")) body = { can_author:true, items:[{ slug:"resource-draft", title:"Resources", version }] };
    else if (path.endsWith("/revisions")) body = { items:[], next_offset:null };
    else if (path.endsWith("/resources")) {
      expect(req.postDataJSON()).toMatchObject({ kind:"word_sense", resource_id:id, values:{ explanation_english:"Updated original explanation" }, next_version:"0.1.1" });
      version = "0.1.1"; body = { version };
    } else if (path.endsWith("/course")) {
      expect(req.postDataJSON()).toMatchObject({ level:"A1", source_license:"Original draft license, review pending", next_version:"0.1.2" });
      version = "0.1.2"; body = { version };
    } else if (path.endsWith("/resource-draft")) body = { can_author:true, digest:version.padEnd(64,"a"), categories:[], technical_issues:[], history:[],
      readiness:{ outstanding:[], complete:false, independent_licensing:false }, content:{ title:"Resources", description:"Original draft",
        estimated_minutes:10, level:"A1", source_license:"Original unpublished", attribution:"Original authored examples", source_url:null, version,
        lessons:[{ id, slug:"lesson", title:"Lesson", description:"Original", estimated_minutes:10, prerequisites:[], sections:[], exercises:[] }],
        resources:[{ kind:"word_sense", id, editable:true, values:{ explanation_english:"Original explanation" } }] } };
    await route.fulfill({ json:body, headers });
  });
  await page.goto("/profile/curriculum-review");
  await page.getByRole("button", { name:"Resources · 0.1.0" }).click();
  await page.getByText("Edit lesson details or exercise definition", { exact:true }).click();
  await page.getByLabel("Draft item", { exact:true }).selectOption(`word_sense:${id}`);
  const fields = page.getByLabel("Selected draft fields", { exact:true });
  const edit = JSON.parse(await fields.inputValue()); edit.values.explanation_english = "Updated original explanation";
  await fields.fill(JSON.stringify(edit));
  await page.getByLabel("Structured content version", { exact:true }).fill("0.1.1");
  await page.getByRole("button", { name:"Save structured draft revision" }).click();
  await expect(page.getByText(/Version 0.1.1/)).toBeVisible();
  await page.getByText("Edit lesson details or exercise definition", { exact:true }).click();
  await page.getByLabel("Draft item", { exact:true }).selectOption("course");
  const course = JSON.parse(await fields.inputValue()); course.source_license = "Original draft license, review pending";
  await fields.fill(JSON.stringify(course));
  await page.getByLabel("Structured content version", { exact:true }).fill("0.1.2");
  await page.getByRole("button", { name:"Save structured draft revision" }).click();
  await expect(page.getByText(/Version 0.1.2/)).toBeVisible();
});
