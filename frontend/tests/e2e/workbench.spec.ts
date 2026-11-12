import { test, expect } from "@playwright/test";
import { createHmac } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { waitForMailLink } from "./mailpit";
function totp(secret: string): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const character of secret.toUpperCase().replace(/=|\s/g, ""))
    bits += alphabet.indexOf(character).toString(2).padStart(5, "0");
  const bytes = Buffer.from(
    (bits.match(/.{8}/g) || []).map((byte) => parseInt(byte, 2)),
  );
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = createHmac("sha1", bytes).update(counter).digest();
  const offset = digest[digest.length - 1] & 15;
  return ((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000)
    .toString()
    .padStart(6, "0");
}
async function screenshot(page: import("@playwright/test").Page, name: string) {
  const directory = resolve("../tests/screenshots/personas");
  await mkdir(directory, { recursive: true });
  await page.screenshot({
    path: resolve(directory, `${name}.png`),
    fullPage: true,
  });
}
test("public routes have meaningful real forms and no demo workbench", async ({
  page,
}) => {
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Engine Ready|Nominal|Predicted uptime|downtime saved/),
  ).toHaveCount(0);
  await page.goto("/signup");
  await expect(
    page.getByRole("button", { name: "Create account", exact: true }),
  ).toBeVisible();
  await page.goto("/forgot-password");
  await expect(
    page.getByRole("button", { name: "Request reset link" }),
  ).toBeVisible();
  await page.goto("/invite");
  await expect(page.getByRole("alert")).toContainText("incomplete");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await screenshot(page, "public-mobile-sign-in");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
test("real signup, SMTP verification, MFA, truthful empty state, and machine/job lifecycle", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const unique = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const email = `e2e-${unique}@example.org`;
  const password = `Test-only!${unique}Strong`;
  await page.goto("/signup");
  await page.getByLabel("Your name").fill("Test-only Owner");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Organization name").fill(`Test-only Plant ${unique}`);
  await page.getByLabel("Password", { exact: false }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Check your email" }),
  ).toBeVisible();
  const verification = new URL(
    await waitForMailLink(request, email, "/verify-email"),
  );
  await page.goto(verification.pathname + verification.search);
  await page.getByRole("button", { name: "Verify email address" }).click();
  await expect(
    page.getByRole("heading", { name: "Email verified" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Continue to sign in" }).click();
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByText("No open jobs")).toBeVisible();
  await expect(
    page.getByRole("link", { name: /0 Machines recorded/ }),
  ).toBeVisible();
  await screenshot(page, "owner-empty-workbench");
  await page.getByRole("link", { name: "Set up authenticator" }).click();
  await page.getByLabel("Confirm your password").fill(password);
  await page
    .getByRole("button", { name: "Set up authenticator", exact: true })
    .click();
  await expect(page.getByLabel("Authenticator setup key")).toBeVisible();
  const secret = await page.getByLabel("Authenticator setup key").inputValue();
  await page.getByLabel("Six-digit authenticator code").fill(totp(secret));
  await page.getByRole("button", { name: "Enable authenticator" }).click();
  await expect(
    page.getByRole("heading", { name: "Save your recovery codes" }),
  ).toBeVisible();
  const recovery = (await page.locator(".recovery-codes").textContent())!
    .trim()
    .split(/\s+/)[0];
  await page.getByLabel("I have saved my recovery codes").check();
  await page.getByRole("link", { name: "Open workbench", exact: true }).click();
  await page.getByRole("link", { name: "Machines", exact: true }).click();
  await page
    .getByRole("button", { name: "Record machine", exact: true })
    .click();
  await page.getByLabel("Machine name").fill("Test-only Pump");
  await page.getByLabel("Machine code").fill(`TEST-${unique}`);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Record machine", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: /Test-only Pump/ }).first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: /Test-only Pump/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Not connected" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Create job", exact: true }).click();
  await page.getByLabel("Job title").fill("Test-only inspect pump");
  await page
    .getByLabel("Assigned person")
    .selectOption({ label: "Test-only Owner (owner)" });
  await page.getByLabel("Step 1", { exact: true }).fill("Test-only check seal");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create job", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Test-only inspect pump" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start work", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Start work" })
    .click();
  await expect(
    page.getByText("In progress", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Submit for review", exact: true })
    .click();
  await page.getByRole("dialog").getByLabel("Test-only check seal").check();
  await page
    .getByLabel("Completion notes")
    .fill("Test-only inspection completed.");
  await page.getByLabel("Time spent (minutes)").fill("12");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Submit for review" })
    .click();
  await page
    .getByRole("button", { name: "Approve completion", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Approve completion" })
    .click();
  await expect(page.getByRole("button", { name: "Reopen job", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve completion", exact: true })).toHaveCount(0);
  await expect(page.getByText("Approve by Test-only Owner", { exact: false })).toBeVisible();
  await screenshot(page, "owner-completed-job");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("link", { name: "Today", exact: true }).click();
  await expect(page.getByRole("link", { name: /1 Machines recorded/ })).toBeVisible();
  await expect(page.locator('.sidebar .nav-label-mobile').filter({ hasText: /^Jobs$/ })).toBeVisible();
  for (const label of await page.locator('.sidebar .nav-label-mobile').all()) {
    const box = await label.boundingBox();
    expect(box?.height).toBeLessThan(24);
  }
  await screenshot(page, "owner-mobile-workbench");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Authenticator or recovery code")).toBeVisible();
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Authenticator or recovery code").fill(recovery);
  await page.getByRole("button", { name: "Confirm and sign in" }).click();
  await expect(page).toHaveURL(/\/app/);
});
