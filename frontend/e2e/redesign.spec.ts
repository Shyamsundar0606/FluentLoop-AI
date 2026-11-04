import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("five destinations, responsive pages, focus, appearance and microphone sizing", async ({
  page,
}) => {
  test.skip(
    process.env.SPEECH_E2E_REAL_API !== "1",
    "Uses the isolated API and test account",
  );
  test.setTimeout(120_000);
  await page.goto("/login");
  await page.getByLabel("Email").fill("ai-browser@example.com");
  await page
    .locator('input[autocomplete="current-password"]')
    .fill("IsolatedBrowserTest2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  for (const width of [1440, 900, 390, 320]) {
    await page.setViewportSize({ width, height: 960 });
    for (const route of [
      "/dashboard",
      "/courses",
      "/ai-tutor",
      "/voice-practice",
      "/profile",
    ]) {
      await page.goto(route);
      const nav = page.getByRole("navigation", { name: "Main navigation" });
      await expect(nav.getByRole("link")).toHaveCount(5);
      expect(
        (await nav.getByRole("link").allTextContents()).map((text) =>
          text.trim(),
        ),
      ).toEqual(["Home", "Learn", "AI Tutor", "Speak", "Profile"]);
      await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
      await expect(page.locator("main h1")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        `${route} at ${width}px`,
      ).toBe(true);
      if (route === "/dashboard") {
        await expect(
          page.getByRole("heading", { name: "Bonjour, Browser!" }),
        ).toBeVisible();
        await expect(
          page.locator(".app-content:visible .progress-stats strong").first(),
        ).toHaveText(/^\d+$/);
        if (process.env.UI_SCREENSHOTS === "1" && [1440, 390].includes(width)) {
          mkdirSync("../docs/verification/frontend-redesign", {
            recursive: true,
          });
          await page.screenshot({
            path: `../docs/verification/frontend-redesign/home-${width}.png`,
            fullPage: true,
          });
        }
      }
    }
  }
  await page.locator(".skip-link").focus();
  await expect(page.locator(".skip-link")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.locator("#page-content")).toBeFocused();
  await page.goto("/voice-practice");
  await page.getByRole("button", { name: "Start Voice Conversation" }).click();
  const mic = page.getByRole("button", { name: "Record French" });
  await expect(mic).toBeVisible();
  const size = await mic.boundingBox();
  expect(size!.width).toBeGreaterThanOrEqual(100);
  expect(size!.height).toBeGreaterThanOrEqual(100);
  if (process.env.UI_SCREENSHOTS === "1")
    await page.screenshot({
      path: "../docs/verification/frontend-redesign/speak-320.png",
      fullPage: true,
    });
  await page.getByRole("banner").getByLabel("Account options").click();
  await page.getByRole("banner").getByLabel("Toggle theme").click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link")
      .first()
      .evaluate((el) => getComputedStyle(el).transitionDuration),
  ).toBe("0s");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
});
