import { test, expect } from "@playwright/test";
import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";
import { createHmac, randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { waitForMailLink } from "./mailpit";

async function post(request: APIRequestContext, path: string, data: unknown, expected = 200) {
  const token = (await (await request.get("/api/v1/csrf")).json()).csrf_token;
  const response = await request.post(`/api/v1${path}`, { data, headers: { "X-CSRF-Token": token } });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(expected);
  return response.json();
}
function code(secret: string) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const bits = [...secret].map((letter) => alphabet.indexOf(letter).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from((bits.match(/.{8}/g) || []).map((value) => parseInt(value, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const hash = createHmac("sha1", key).update(counter).digest();
  return ((hash.readUInt32BE(hash[hash.length - 1] & 15) & 0x7fffffff) % 1000000).toString().padStart(6, "0");
}
async function account(context: BrowserContext, label: string, stamp: string) {
  const email = `security-${label}-${stamp}@example.test`;
  const password = `Security-fixture!${stamp}-${label}-42`;
  const created = await post(context.request, "/auth/signup", { email, password, name: `Test ${label}`, company_name: `Test security plant ${label} ${stamp}` }, 201);
  const verification = new URL(await waitForMailLink(context.request, email, "/verify-email"));
  await post(context.request, "/auth/verify-email", { token: verification.searchParams.get("token") });
  await post(context.request, "/auth/login", { email, password });
  const setup = await post(context.request, "/auth/mfa/setup", { password });
  const enrolled = await post(context.request, "/auth/mfa/confirm", { code: code(setup.secret) });
  return { email, password, companyId: created.company.id as number, recovery: enrolled.recovery_codes as string[] };
}
async function confirm(page: Page, password: string, recovery: string) {
  await page.getByLabel("Confirm your password").fill(password);
  await page.getByLabel("Authenticator or recovery code").fill(recovery);
  await page.getByRole("button", { name: "Confirm identity", exact: true }).click();
  await expect(page.getByLabel("Reason for this access change")).toBeVisible();
}
async function screenshot(page: Page, name: string) {
  const directory = resolve("../tests/screenshots/personas");
  await mkdir(directory, { recursive: true });
  await page.screenshot({ path: resolve(directory, name + ".png"), fullPage: true });
}

test("owner offboards a factory membership, protects last owner and cancels an invitation", async ({ browser, baseURL }) => {
  test.setTimeout(180000);
  const stamp = randomUUID().slice(0, 12);
  const origin = baseURL || "http://localhost:5173";
  const ownerContext = await browser.newContext({ baseURL: origin });
  const personContext = await browser.newContext({ baseURL: origin });
  const ownFactoryContext = await browser.newContext({ baseURL: origin });
  try {
    const owner = await account(ownerContext, "owner", stamp);
    const person = await account(personContext, "colleague", stamp);
    await post(ownFactoryContext.request, "/auth/login", { email: person.email, password: person.password, totp_code: person.recovery[0] });
    await post(ownerContext.request, "/invitations", { email: person.email, role: "technician" }, 201);
    const invitation = new URL(await waitForMailLink(personContext.request, person.email, "/invite"));
    await post(personContext.request, "/invitations/accept", { token: invitation.searchParams.get("token") });
    await post(personContext.request, "/companies/switch", { company_id: owner.companyId });
    const personPage = await personContext.newPage();
    await personPage.goto("/app");
    await expect(personPage.getByRole("heading", { name: "A clear view of the work." })).toBeVisible();
    const page = await ownerContext.newPage();
    await page.goto("/app/team");
    await page.getByRole("button", { name: "Remove Test colleague", exact: true }).click();
    await confirm(page, owner.password, owner.recovery[0]);
    await page.getByLabel("Reason for this access change").fill("Test-only offboarding rehearsal");
    await page.getByRole("button", { name: "Remove member", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("cell", { name: person.email, exact: true })).toHaveCount(0);
    await screenshot(page, "security-owner-offboarding");
    await personPage.reload();
    await expect(personPage).toHaveURL(/\/login/);
    expect((await personContext.request.get("/api/v1/assets")).status()).toBe(401);
    const stillValid = await ownFactoryContext.request.get("/api/v1/auth/me");
    expect(stillValid.status()).toBe(200);
    expect((await stillValid.json()).company.id).toBe(person.companyId);

    await page.getByRole("button", { name: "Remove Test owner", exact: true }).click();
    await confirm(page, owner.password, owner.recovery[1]);
    await page.getByLabel("Reason for this access change").fill("Test last owner safety control");
    await page.getByRole("button", { name: "Remove member", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(/owner/i);
    await page.getByRole("button", { name: "Keep current access", exact: true }).click();

    const pending = `cancel-${stamp}@example.test`;
    await post(ownerContext.request, "/invitations", { email: pending, role: "viewer" }, 201);
    const pendingLink = new URL(await waitForMailLink(ownerContext.request, pending, "/invite"));
    await page.reload();
    await page.getByRole("button", { name: `Cancel invitation for ${pending}`, exact: true }).click();
    await confirm(page, owner.password, owner.recovery[2]);
    await page.getByLabel("Reason for this access change").fill("Test-only invitation cancellation");
    await page.getByRole("dialog").getByRole("button", { name: "Cancel invitation", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("cell", { name: pending, exact: true })).toHaveCount(0);
    const cancelled = await personContext.request.get(`/api/v1/invitations/preview?token=${pendingLink.searchParams.get("token")}`);
    expect(cancelled.status()).toBe(400);
    await screenshot(page, "security-cancelled-invitation");
  } finally {
    await Promise.all([ownerContext, personContext, ownFactoryContext].map((context) => context.close()));
  }
});
