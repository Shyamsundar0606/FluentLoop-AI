import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("privacy export downloads an owned page and deletion requires explicit confirmation (mock API)", async ({ page }) => {
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";
  const origin = new URL(process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001").origin;
  let deleted = false;
  let exports = 0;
  await page.route(`${api}/**`, async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    const headers = { "access-control-allow-origin": origin, "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,POST,OPTIONS", "access-control-allow-headers": "content-type,x-csrf-token" };
    if (request.method()==="OPTIONS") { await route.fulfill({ status:200, headers }); return; }
    let body: unknown = {};
    if (path.endsWith("/auth/me")) body = { user: { id:"privacy", email:"privacy@example.test", role:"learner",
      email_verified:true, display_name:"Learner", onboarding_completed:true, preferences:{ current_level:"a1", theme:"light" } } };
    else if (path.endsWith("/users/me/preferences")) body = { current_level:"a1", target_language:"French", explanation_language:"English",
      daily_study_minutes:15, learning_focus:"balanced", theme:"light", audio_playback_speed:1 };
    else if (path.endsWith("/auth/sessions")) body = { sessions:[] };
    else if (path.endsWith("/data-export")) {
      if (request.method()==="GET") body = { sections:["profile","writing"], page_limit:100 };
      else {
        expect(request.postDataJSON()).toEqual({ password:"SyntheticOnlyPassword", section:"profile", offset:exports ? 100 : 0 });
        exports++;
        body = { section:"profile", items:[{ display_name:"Learner" }], next_offset:exports===1 ? 100 : null, notice:"No credentials or curriculum keys." };
      }
    } else if (path.endsWith("/delete-account")) {
      expect(request.postDataJSON()).toEqual({ password:"SyntheticOnlyPassword", confirmation:"DELETE MY ACCOUNT" });
      deleted = true; body = { receipt:"synthetic-receipt" };
    }
    await route.fulfill({ json:body, headers });
  });
  await page.setViewportSize({ width:320, height:900 });
  await page.goto("/settings");
  const region = page.getByRole("region", { name:"Export or permanently delete your data" });
  await expect(region.getByRole("button", { name:"Download data page" })).toBeDisabled();
  await region.getByLabel("Confirm current password", { exact:true }).fill("SyntheticOnlyPassword");
  const download = page.waitForEvent("download");
  await region.getByRole("button", { name:"Download data page" }).click();
  expect((await download).suggestedFilename()).toBe("fluentloop-profile-0.json");
  await expect(region.getByRole("status")).toContainText("More records are available");
  await expect(region.getByLabel("Confirm current password", { exact:true })).toHaveValue("");
  await region.getByRole("button", { name:"Select next page" }).click();
  await region.getByLabel("Confirm current password", { exact:true }).fill("SyntheticOnlyPassword");
  await region.getByRole("button", { name:"Download data page" }).click();
  await expect(region.getByRole("status")).toContainText("no further pages");
  await region.getByText("Permanently delete account", { exact:true }).click();
  const remove = region.getByRole("button", { name:"Permanently delete my account" });
  await expect(remove).toBeDisabled();
  await region.getByLabel("Confirm current password", { exact:true }).fill("SyntheticOnlyPassword");
  await region.getByLabel("Type DELETE MY ACCOUNT to confirm", { exact:true }).fill("yes");
  await expect(remove).toBeDisabled();
  expect(deleted).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
  const accessibility = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(accessibility.violations).toEqual([]);
  await region.getByLabel("Type DELETE MY ACCOUNT to confirm", { exact:true }).fill("DELETE MY ACCOUNT");
  await remove.focus(); await remove.press("Enter");
  await expect(page).toHaveURL(/\/login$/);
  expect(deleted).toBe(true);
});
