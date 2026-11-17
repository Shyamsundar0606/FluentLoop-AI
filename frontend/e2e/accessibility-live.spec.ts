import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.use({ trace: "off" });
test.skip(process.env.RC_ACCESSIBILITY_E2E !== "1", "Requires an explicitly disposable authorized demo.");

test("public and authorized learner routes satisfy automated WCAG2.2AA checks and mobile layout", async ({ page }) => {
  test.setTimeout(600_000);
  const failures: { path: string; width: number; rule: string; targets: string[][] }[] = [];
  const check = async (path: string, width: number) => {
    await page.setViewportSize({ width, height: 960 });
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main h1").first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1), `${path} at ${width}px`).toBe(true);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a","wcag2aa","wcag21aa","wcag22aa"]).analyze();
    for (const violation of result.violations) failures.push({ path, width, rule: violation.id,
      targets: violation.nodes.map(node => node.target as string[]) });
  };
  for (const path of ["/register","/login","/forgot-password","/verify-email","/reset-password"]) {
    for (const width of [320,1440]) await check(path,width);
  }
  const fixture = JSON.parse(readFileSync(resolve("../.publication-private/m08/m09-manual-fixture.json"),"utf8"));
  await page.goto("/login");
  await page.getByLabel("Email").fill(fixture.email);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8012/api/v1";
  const catalog = await (await page.request.get(`${api}/learning/assessments`)).json();
  const lesson = catalog.items.find((item: { skill: string }) => item.skill==="grammar").lesson_id;
  for (const path of ["/onboarding","/dashboard","/courses",`/lessons/${lesson}`,"/grammar","/vocabulary",
    "/practice","/assessments","/ai-tutor","/ai-tutor/scenarios","/voice-practice","/progress","/profile","/settings"]) {
    for (const width of [320,390,900,1440]) await check(path,width);
  }
  await page.emulateMedia({ reducedMotion:"reduce" });
  await page.goto("/dashboard");
  await page.locator(".skip-link").focus();
  await expect(page.locator(".skip-link")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.locator("#page-content")).toBeFocused();
  expect(await page.getByRole("navigation",{name:"Main navigation"}).getByRole("link").first()
    .evaluate(node=>getComputedStyle(node).transitionDuration)).toBe("0s");
  expect(failures).toEqual([]);
});
