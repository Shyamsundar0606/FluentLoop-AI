import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";

test.use({ trace: "off" });
test.skip(process.env.RC_MAIL_E2E !== "1", "Requires the explicitly disposable mail-enabled RC demo.");
const api = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8012/api/v1";
const origin = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3012";

async function mailToken(request: APIRequestContext, email: string, kind: "verification" | "reset") {
  let token = "";
  await expect.poll(async () => {
    const inbox = await (await request.get("http://127.0.0.1:8025/api/v1/messages?limit=100")).json();
    for (const message of inbox.messages ?? []) {
      if (!JSON.stringify(message).includes(email)) continue;
      const detail = await (await request.get(`http://127.0.0.1:8025/api/v1/message/${message.ID}`)).json();
      token = JSON.stringify(detail).match(kind === "reset" ? /reset-password#token=([A-Za-z0-9_-]+)/ : /verify-email#token=([A-Za-z0-9_-]+)/)?.[1] ?? "";
      if (token) return true;
    }
    return false;
  }).toBe(true);
  return token;
}

function expire(email: string, kind: "verification" | "reset", token: string) {
  execFileSync(resolve("../.venv312/Scripts/python.exe"), [resolve("../backend/scripts/rc_test_controls.py")], {
    input: JSON.stringify({ action: "expire", email, kind, token }), encoding: "utf8",
    env: { ...process.env, RC_DISPOSABLE_TEST: "1" },
  });
}

test("real email links enforce expiration, reset, duplicate registration and rate limits", async ({ page, request }) => {
  test.setTimeout(120_000);
  const email = `rc-mail-${Date.now()}@example.com`, password = "SyntheticMailTest2026!", changed = "ChangedSyntheticMail2026!";
  const post = (path: string, data: unknown) => request.post(`${api}/auth/${path}`, { headers: { Origin: origin }, data });
  const registration = { email, password, confirm_password: password, display_name: "Synthetic mail learner" };
  expect((await post("register", registration)).status()).toBe(201);
  const initial = await mailToken(request, email, "verification");
  const duplicate = await post("register", registration);
  expect(duplicate.status()).toBe(409);
  expect(await duplicate.json()).toEqual({ detail: "Unable to register with this email address." });
  expire(email, "verification", initial);
  expect((await post("verify-email", { token: initial })).status()).toBe(400);
  expect((await post("verify-email", { token: "invalid" })).status()).toBe(422);
  expect((await post("verify-email", { token: "x".repeat(43) })).status()).toBe(400);
  expect((await post("login", { email, password })).status()).toBe(403);
  expect((await post("resend-verification", { email })).status()).toBe(200);
  const verification = await mailToken(request, email, "verification");
  expect(verification).not.toBe(initial);
  expect((await post("verify-email", { token: verification })).status()).toBe(200);
  expect((await post("verify-email", { token: verification })).status()).toBe(400);
  expect((await post("login", { email, password })).status()).toBe(200);
  await page.goto("/forgot-password");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("status")).toContainText("reset instructions");
  const expired = await mailToken(request, email, "reset");
  expire(email, "reset", expired);
  expect((await post("reset-password", { token: expired, password: changed, confirm_password: changed })).status()).toBe(400);
  expect((await post("forgot-password", { email })).status()).toBe(200);
  const reset = await mailToken(request, email, "reset");
  expect(reset).not.toBe(expired);
  await page.goto(`/reset-password#token=${reset}`);
  await page.getByLabel("New password", { exact: true }).fill(changed);
  await page.getByLabel("Confirm new password", { exact: true }).fill(changed);
  await page.getByRole("button", { name: "Reset password", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Your password was reset");
  expect((await post("reset-password", { token: reset, password, confirm_password: password })).status()).toBe(400);
  expect((await post("login", { email, password })).status()).toBe(401);
  expect((await post("login", { email, password: changed })).status()).toBe(200);
  expect((await post("forgot-password", { email: "rc-mail-missing@example.com" })).status()).toBe(200);
  const limited = await post("forgot-password", { email });
  expect(limited.status()).toBe(429);
  expect(Number(limited.headers()["retry-after"])).toBeGreaterThan(0);
});
