import { expect, test } from "@playwright/test";

test("real API with fake provider: login, persistence, correction, sources and owner isolation", async ({
  page,
}) => {
  test.skip(
    process.env.AI_E2E_REAL_API !== "1",
    "Requires explicitly isolated M05 browser API",
  );
  test.setTimeout(90_000);
  async function signIn(email: string) {
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page
      .locator('input[autocomplete="current-password"]')
      .fill("IsolatedBrowserTest2026!");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
  }
  await signIn("ai-browser@example.com");
  await page.goto("/ai-tutor");
  await page.getByLabel("Practice mode").selectOption("grammar");
  await page.getByLabel("Your question").fill("Explain bonjour");
  await page.getByRole("button", { name: "Start a new conversation" }).click();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  const savedURL = page.url();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Être means to be");
  await expect(
    page.getByText(/Draft preview: this conversation/),
  ).toBeVisible();
  const source = page
    .getByRole("list", { name: "Conversation messages" })
    .getByRole("link")
    .first();
  await expect(source).toHaveAttribute("href", /\/lessons\//);
  await source.click();
  await expect(
    page.getByRole("link", { name: /Start interactive lesson|Resume lesson/ }),
  ).toBeVisible();
  await page.goto(savedURL);
  await page.reload();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Explain bonjour");
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("One more example");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("One more example");
  await page.goto("/ai-tutor/history");
  await page
    .getByRole("link", { name: "Explain bonjour", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("One more example");
  await page.goto("/ai-tutor");
  await page.getByLabel("Practice mode").selectOption("correction");
  await page.getByLabel("Your question").fill("Je suis 24 ans.");
  await page.getByRole("button", { name: "Start a new conversation" }).click();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("Original: Je suis 24 ans.")).toBeVisible();
  await page.goto("/ai-tutor/scenarios");
  await page.getByRole("button", { name: "Start practice" }).first().click();
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toContainText("Bonjour");
  await page.goto("/ai-tutor/recommendations");
  await page.getByRole("button", { name: "Refresh recommendations" }).click();
  await expect(
    page.getByText(/not enough repeated-error evidence/),
  ).toBeVisible();
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await signIn("ai-other@example.com");
  await page.goto(savedURL);
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "Conversation not found.",
  );
  await expect(
    page.getByRole("list", { name: "Conversation messages" }),
  ).toHaveCount(0);
});
