import { expect, test } from "@playwright/test";

test("local login renders without external font services", async ({ page }) => {
  const external: string[] = [];
  await page.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (!["127.0.0.1", "localhost", "::1"].includes(url.hostname)) {
      external.push(url.hostname);
      await route.abort();
    } else {
      await route.continue();
    }
  });
  await page.goto("/login");
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(external).toEqual([]);
});
