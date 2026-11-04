import { APIRequestContext, expect, test } from "@playwright/test";

test("registration validates full name and optional age before submitting minimized input", async ({
  page,
}) => {
  const submissions: Record<string, unknown>[] = [];
  await page.route(
    `${process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1"}/auth/register`,
    async (route) => {
      const headers = {
        "access-control-allow-origin": new URL(
          process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001",
        ).origin,
        "access-control-allow-credentials": "true",
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "content-type",
      };
      if (route.request().method() !== "OPTIONS")
        submissions.push(route.request().postDataJSON());
      await route.fulfill({
        status: route.request().method() === "OPTIONS" ? 200 : 201,
        headers,
        contentType: "application/json",
        body: "{}",
      });
    },
  );
  await page.goto("/register");
  await page.getByLabel("Full name").fill("   ");
  await page
    .getByLabel("Email", { exact: true })
    .fill("optional-age@example.com");
  await page.getByLabel(/^Password/).fill("RegistrationTest2026");
  await page.getByLabel("Confirm password").fill("RegistrationTest2026");
  await page.getByRole("button", { name: "Create free account" }).click();
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "Full name is required.",
  );
  expect(submissions).toHaveLength(0);
  await page.getByLabel("Full name").fill("  Alice Dupont  ");
  const age = page.getByLabel("Age (optional)");
  await expect(age).not.toHaveAttribute("required");
  await age.fill("17.5");
  expect(await age.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(
    false,
  );
  await age.fill("");
  await page.getByRole("button", { name: "Create free account" }).click();
  await expect(page.getByRole("status")).toContainText("Registration received");
  expect(submissions).toHaveLength(1);
  expect(submissions[0]).toMatchObject({
    full_name: "Alice Dupont",
    age: null,
  });
  expect(submissions[0]).not.toHaveProperty("birth_date");
});

test("registration and login explain rate limits and use the retry delay", async ({
  page,
}) => {
  await page.route(
    `${process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1"}/auth/**`,
    async (route) => {
      const request = route.request();
      const headers = {
        "access-control-allow-origin": new URL(
          process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001",
        ).origin,
        "access-control-allow-credentials": "true",
      };
      if (request.method() === "OPTIONS") {
        await route.fulfill({
          status: 200,
          headers: {
            ...headers,
            "access-control-allow-methods": "POST",
            "access-control-allow-headers": "content-type",
          },
        });
        return;
      }
      await route.fulfill({
        status: 429,
        headers: {
          ...headers,
          "access-control-expose-headers": "Retry-After",
          "retry-after": "120",
        },
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Too many requests. Please try again later.",
        }),
      });
    },
  );

  await page.goto("/register");
  await page.getByLabel("Full name").fill("Rate limited learner");
  await page
    .getByLabel("Email", { exact: true })
    .fill("rate-limit@example.com");
  await page.getByLabel(/^Password/).fill("FluentLoopE2E2026");
  await page.getByLabel("Confirm password").fill("FluentLoopE2E2026");
  await page.getByRole("button", { name: "Create free account" }).click();
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "Too many attempts. Please try again in about 2 minutes.",
  );

  await page.goto("/login");
  await page.getByLabel("Email").fill("rate-limit@example.com");
  await page
    .locator('input[autocomplete="current-password"]')
    .fill("FluentLoopE2E2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator('p[role="alert"]')).toHaveText(
    "Too many attempts. Please try again in about 2 minutes.",
  );
});

async function getVerificationToken(
  request: APIRequestContext,
  email: string,
): Promise<string> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const inbox = await request.get(
      "http://127.0.0.1:8025/api/v1/messages?limit=50",
    );
    expect(inbox.ok()).toBeTruthy();
    const payload = await inbox.json();
    const candidate = (payload.messages ?? []).find((message: unknown) =>
      JSON.stringify(message).toLowerCase().includes(email.toLowerCase()),
    );
    if (candidate) {
      const id = candidate.ID ?? candidate.id;
      const detailResponse = await request.get(
        `http://127.0.0.1:8025/api/v1/message/${id}`,
      );
      expect(detailResponse.ok()).toBeTruthy();
      const detail = await detailResponse.json();
      const text = JSON.stringify(detail);
      const token = text.match(/verify-email#token=([A-Za-z0-9_-]+)/)?.[1];
      if (token) return token;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(
    "Verification email was not available in the local test inbox.",
  );
}

test("register, verify, sign in, onboard, edit profile, and sign out", async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  const email = `milestone02-${Date.now()}@example.com`;
  const password = "FluentLoopE2E2026";
  const displayName = "E2E Learner";

  await page.goto("/register");
  await page.getByLabel("Full name").fill(displayName);
  await page.getByLabel("Age (optional)").fill("24");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Create free account" }).click();
  await expect(page.getByRole("status")).toContainText("Registration received");

  const verificationToken = await getVerificationToken(request, email);
  await page.goto(`/verify-email#token=${verificationToken}`);
  await page.getByRole("button", { name: "Verify or resend link" }).click();
  await expect(page.getByRole("status")).toContainText("Email verified");

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page
    .locator('input[autocomplete="current-password"]')
    .fill("incorrect-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByText("Invalid email or password.", { exact: true }),
  ).toBeVisible();

  await page.locator('input[autocomplete="current-password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(
    page.getByRole("heading", { name: "Welcome", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      `Hello, ${displayName}. Your registered name is already saved.`,
    ),
  ).toBeVisible();
  await expect(page.getByLabel("Full name")).toHaveCount(0);
  for (let step = 0; step < 5; step += 1) {
    if (step === 1) {
      await expect(page.getByRole("radio")).toHaveCount(6);
      await expect(page.getByRole("radio", { name: "A1" })).toBeChecked();
      await page.getByRole("radio", { name: "B1" }).check();
    }
    await page.getByRole("button", { name: "Continue" }).click();
  }
  await page.getByRole("button", { name: "Save and open dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", {
      name: `Bonjour, ${displayName.split(" ")[0]}!`,
    }),
  ).toBeVisible();
  await expect(
    page
      .locator(".app-shell:visible .topbar-tools .level-badge")
      .filter({ hasText: "B1" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Learn", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "French courses" }),
  ).toBeVisible();
  await expect(page.getByText("No published B1 courses yet")).toBeVisible();
  await page.getByLabel("Browse French level").selectOption("c2");
  await expect(page.getByText("No published C2 courses yet")).toBeVisible();
  await expect(
    page.getByText(
      "Your saved level is B1. Browsing another level does not update it.",
    ),
  ).toBeVisible();
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("link", { name: /Practice speaking/ }),
  ).toBeVisible();

  await page.goto("/onboarding");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("radio", { name: "B1" })).toBeChecked();
  for (let step = 0; step < 3; step += 1) {
    await page.getByRole("button", { name: "Continue" }).click();
  }
  await expect(
    page.getByRole("radio", { name: "15 minutes per day" }),
  ).toBeChecked();
  await page.goto("/dashboard");
  await page.getByText("Learning preferences", { exact: true }).click();
  await page.getByLabel("Change your French level").selectOption("a2");
  await page.getByRole("button", { name: "Save level" }).click();
  await expect(page.getByRole("status").filter({ hasText: "French level updated." })).toHaveText("French level updated.");
  await expect(
    page
      .locator(".app-shell:visible .topbar-tools .level-badge")
      .filter({ hasText: "A2" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Profile", exact: true }).click();
  await page
    .getByRole("navigation", { name: "Profile sections" })
    .getByRole("link", { name: "Settings", exact: true })
    .click();
  const settingsLevel = page.getByLabel("Current French level");
  await expect(settingsLevel.locator("option")).toHaveCount(6);
  await expect(settingsLevel).toHaveValue("a2");
  await settingsLevel.selectOption("c1");
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByRole("status")).toHaveText("Preferences saved.");
  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page
      .locator(".app-shell:visible .topbar-tools .level-badge")
      .filter({ hasText: "C1" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Profile", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your profile" }),
  ).toBeVisible();
  await page.getByLabel("Preferred name (optional)").fill("Fluent Friend");
  await page
    .getByLabel("Display name", { exact: true })
    .fill("Updated Learner");
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByRole("status")).toContainText("Profile saved");

  await page.getByRole("link", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", { name: "Bonjour, Updated!" }),
  ).toBeVisible();
  await page.goto("/ai-tutor");
  await expect(
    page.getByText("Welcome, Updated Learner. Ready to practice French?"),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Welcome, Updated Learner. Ready to practice French?"),
  ).toBeVisible();
  await page.goto("/dashboard");
  await page.getByRole("link", { name: "Profile", exact: true }).click();
  await page
    .getByRole("navigation", { name: "Profile sections" })
    .getByRole("link", { name: "Settings", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out all devices" }).click();
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?next=/);
});
