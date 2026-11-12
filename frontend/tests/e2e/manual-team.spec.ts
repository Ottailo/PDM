import { test, expect } from "@playwright/test";
import type {
  APIRequestContext,
  Browser,
  BrowserContext,
  Page,
} from "@playwright/test";
import { createHmac, randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { waitForMailLink } from "./mailpit";

// Explicit synthetic test records in the real local pilot DB. No route mocks.
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const FIXTURE = process.env.PDM_MANUAL_FIXTURE || resolve(ROOT, ".pilot/fixtures/manual-test-only.pdf");
interface Persona {
  context: BrowserContext;
  page: Page;
  email: string;
  password: string;
  companyId?: number;
}
function authenticatorCode(secret: string): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const bits = [...secret.toUpperCase().replace(/[=\s]/g, "")]
    .map((character) =>
      alphabet.indexOf(character).toString(2).padStart(5, "0"),
    )
    .join("");
  const key = Buffer.from(
    (bits.match(/.{8}/g) || []).map((byte) => Number.parseInt(byte, 2)),
  );
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const hash = createHmac("sha1", key).update(counter).digest();
  return (
    (hash.readUInt32BE(hash[hash.length - 1] & 15) & 0x7fffffff) %
    1000000
  )
    .toString()
    .padStart(6, "0");
}
async function write(
  request: APIRequestContext,
  path: string,
  data: unknown,
  expected = 200,
  method = "POST",
) {
  const csrfResponse = await request.get("/api/v1/csrf");
  expect(csrfResponse.status(), "Real CSRF endpoint must be available").toBe(
    200,
  );
  const { csrf_token } = (await csrfResponse.json()) as { csrf_token: string };
  const response = await request.fetch(`/api/v1${path}`, {
    method,
    data,
    headers: {
      "X-CSRF-Token": csrf_token,
      ...(path.startsWith("/work-orders")
        ? { "Idempotency-Key": randomUUID() }
        : {}),
    },
  });
  expect(response.status(), `${method} ${path}: ${await response.text()}`).toBe(
    expected,
  );
  return response;
}
async function persona(
  browser: Browser,
  baseURL: string,
  email: string,
  password: string,
): Promise<Persona> {
  const context = await browser.newContext({ baseURL });
  context.setDefaultTimeout(15000);
  return { context, page: await context.newPage(), email, password };
}
async function owner(
  browser: Browser,
  baseURL: string,
  stamp: string,
  label: string,
): Promise<Persona> {
  const person = await persona(
    browser,
    baseURL,
    `manual-${label}-${stamp}@example.test`,
    `Test-only!${stamp}-${label}-42Strong`,
  );
  const signup = await write(
    person.context.request,
    "/auth/signup",
    {
      name: `Test-only ${label} owner`,
      email: person.email,
      password: person.password,
      company_name: `Test-only ${label} plant ${stamp}`,
    },
    201,
  );
  person.companyId = (
    (await signup.json()) as { company: { id: number } }
  ).company.id;
  const token = new URL(
    await waitForMailLink(
      person.context.request,
      person.email,
      "/verify-email",
    ),
  ).searchParams.get("token");
  await write(person.context.request, "/auth/verify-email", { token });
  await write(person.context.request, "/auth/login", {
    email: person.email,
    password: person.password,
  });
  const setup = await write(person.context.request, "/auth/mfa/setup", {
    password: person.password,
  });
  const { secret } = (await setup.json()) as { secret: string };
  await write(person.context.request, "/auth/mfa/confirm", {
    code: authenticatorCode(secret),
  });
  // Keep this real enrolled session. Never immediately replay the setup TOTP at login.
  await person.page.goto("/app");
  await expect(
    person.page.getByRole("heading", { name: "A clear view of the work." }),
  ).toBeVisible();
  return person;
}
async function screenshot(page: Page, name: string) {
  const directory = resolve(ROOT, "tests/screenshots/personas");
  await mkdir(directory, { recursive: true });
  await page.screenshot({
    path: resolve(directory, `${name}.png`),
    fullPage: true,
  });
}
async function inviteFromWorkbench(
  ownerPage: Page,
  email: string,
  role: string,
) {
  await ownerPage.goto("/app/team");
  await ownerPage.getByRole("button", { name: "Invite teammate" }).click();
  await ownerPage.getByLabel("Teammate’s work email").fill(email);
  await ownerPage.getByRole("dialog").getByRole("combobox", { name: /^Role/ }).selectOption(role);
  await ownerPage.getByRole("button", { name: "Send invitation" }).click();
  await expect(ownerPage.getByRole("dialog").getByRole("status")).toContainText(
    "Invitation queued",
  );
  await ownerPage.getByRole("button", { name: "Done", exact: true }).click();
}
async function acceptAndLogin(person: Persona, name: string) {
  const invitation = new URL(
    await waitForMailLink(person.context.request, person.email, "/invite"),
  );
  await person.page.goto(invitation.pathname + invitation.search);
  await expect(
    person.page.getByText(person.email, { exact: true }),
  ).toBeVisible();
  await person.page.getByLabel("Your name").fill(name);
  await person.page.getByLabel("Create password").fill(person.password);
  await person.page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(person.page.getByRole("status")).toContainText(
    "Invitation accepted",
  );
  await person.page.getByRole("link", { name: "Sign in", exact: true }).click();
  await person.page.getByLabel("Work email").fill(person.email);
  await person.page.getByLabel(/^Password/).fill(person.password);
  await person.page
    .getByRole("button", { name: "Sign in", exact: true })
    .click();
  await expect(person.page).toHaveURL(/\/app$/);
}
async function currentJob(request: APIRequestContext, id: number) {
  const response = await request.get(`/api/v1/work-orders/${id}`);
  expect(response.status()).toBe(200);
  return (
    (await response.json()) as {
      work_order: { revision: number; status: string };
    }
  ).work_order;
}

test("five real personas: invitation, technician work, private scanned manual, restricted roles, and organization switch", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(420000);
  const stamp = `${Date.now()}-${randomUUID().slice(0, 8)}`;
  const origin = baseURL || "http://localhost:5173";
  const people: Persona[] = [];
  let administrator!: Persona,
    foreign!: Persona,
    technician!: Persona,
    stores!: Persona,
    viewer!: Persona;
  let machineId = 0,
    jobId = 0,
    documentId = 0;
  try {
    await test.step("Owner records a real test machine and sends a real SMTP technician invitation", async () => {
      administrator = await owner(browser, origin, stamp, "manual");
      people.push(administrator);
      const assetResponse = await write(
        administrator.context.request,
        "/assets",
        {
          code: `TEST-PDF-${stamp}`,
          name: "Test-only manual fixture pump",
          description:
            "Synthetic software verification record; not physical equipment.",
        },
        201,
      );
      machineId = ((await assetResponse.json()) as { asset: { id: number } })
        .asset.id;
      technician = await persona(
        browser,
        origin,
        `technician-${stamp}@example.test`,
        `Test-only!Technician-${stamp}-42`,
      );
      people.push(technician);
      await inviteFromWorkbench(
        administrator.page,
        technician.email,
        "technician",
      );
      await acceptAndLogin(technician, "Test-only maintenance technician");
      await technician.page.goto("/app/team");
      await expect(technician.page.getByRole("table")).toContainText(
        "Test-only maintenance technician",
      );
      await expect(
        technician.page.getByRole("button", { name: "Invite teammate" }),
      ).toHaveCount(0);
      await screenshot(technician.page, "technician-real-invitation-accepted");
    });

    await test.step("Technician requests work, owner assigns it, and technician carries out the real lifecycle", async () => {
      await technician.page.goto(
        `/app/maintenance?new=1&asset_id=${machineId}`,
      );
      await expect(technician.page.getByLabel(/^Machine/)).toHaveValue(String(machineId));
      await technician.page.getByLabel(/^Machine/).selectOption(String(machineId));
      await technician.page
        .getByLabel("Job title")
        .fill("Test-only inspect fixture pump");
      await technician.page
        .getByLabel("Step 1", { exact: true })
        .fill("Record TEST-ONLY-42 inspection evidence");
      await expect(technician.page.getByLabel("Assigned person")).toHaveCount(
        0,
      );
      const created = technician.page.waitForResponse(
        (response) =>
          response.url().endsWith("/api/v1/work-orders") &&
          response.request().method() === "POST",
      );
      await technician.page
        .getByRole("dialog")
        .getByRole("button", { name: "Create job", exact: true })
        .click();
      const createdResponse = await created;
      expect(createdResponse.status()).toBe(201);
      jobId = ((await createdResponse.json()) as { work_order: { id: number } })
        .work_order.id;
      await expect(
        technician.page.getByRole("heading", {
          name: "Test-only inspect fixture pump",
        }),
      ).toBeVisible();
      await expect(
        technician.page.getByRole("button", {
          name: "Start work",
          exact: true,
        }),
      ).toHaveCount(0);
      await administrator.page.goto(`/app/maintenance/${jobId}`);
      await administrator.page
        .getByRole("button", { name: "Plan & assign" })
        .click();
      await administrator.page
        .getByLabel("Assigned person")
        .selectOption({
          label: "Test-only maintenance technician (technician)",
        });
      await administrator.page
        .getByRole("button", { name: "Save plan" })
        .click();
      await expect(administrator.page.getByRole("dialog")).toHaveCount(0);
      await technician.page.reload();
      for (const label of ["Start work", "Mark blocked", "Resume work"]) {
        await technician.page
          .getByRole("button", { name: label, exact: true })
          .click();
        if (label === "Mark blocked")
          await technician.page
            .getByLabel("What is blocking the work?")
            .fill("Test-only missing inspection information.");
        await technician.page
          .getByRole("dialog")
          .getByRole("button", { name: label, exact: true })
          .click();
        await expect(technician.page.getByRole("dialog")).toHaveCount(0);
      }
      await technician.page
        .getByRole("button", { name: "Submit for review", exact: true })
        .click();
      await technician.page
        .getByRole("dialog")
        .getByLabel("Record TEST-ONLY-42 inspection evidence")
        .check();
      await technician.page
        .getByLabel("Completion notes")
        .fill(
          "TEST-ONLY-42: synthetic inspection evidence, not engineering instructions.",
        );
      await technician.page.getByLabel("Time spent (minutes)").fill("14");
      await technician.page
        .getByRole("dialog")
        .getByRole("button", { name: "Submit for review", exact: true })
        .click();
      await expect(
        technician.page.getByText("Awaiting review", { exact: true }).first(),
      ).toBeVisible();
      await expect(
        technician.page.getByRole("button", {
          name: "Approve completion",
          exact: true,
        }),
      ).toHaveCount(0);
      const job = await currentJob(technician.context.request, jobId);
      await write(
        technician.context.request,
        `/work-orders/${jobId}/transition`,
        { revision: job.revision, action: "approve" },
        403,
      );
      await screenshot(
        technician.page,
        "technician-submitted-no-self-approval",
      );
      await administrator.page.reload();
      await administrator.page
        .getByRole("button", { name: "Approve completion", exact: true })
        .click();
      await administrator.page
        .getByRole("dialog")
        .getByRole("button", { name: "Approve completion", exact: true })
        .click();
      await expect(administrator.page.getByRole("button", { name: "Reopen job", exact: true })).toBeVisible();
      await expect(administrator.page.getByRole("button", { name: "Approve completion", exact: true })).toHaveCount(0);
      expect((await currentJob(administrator.context.request, jobId)).status).toBe("completed");
    });

    await test.step("Technician uploads the actual PDF, waits for the actual scanner, reads and downloads it", async () => {
      await technician.page.goto(`/app/manuals?asset_id=${machineId}`);
      await technician.page
        .getByRole("button", { name: "Upload PDF", exact: true })
        .click();
      await expect(technician.page.getByRole("dialog").getByLabel(/^Machine/)).toHaveValue(String(machineId));
      await technician.page.getByRole("dialog").getByLabel(/^Machine/).selectOption(String(machineId));
      await technician.page
        .getByLabel("Manual title")
        .fill("Test-only supplier manual TEST-ONLY-42");
      await technician.page.getByLabel("PDF file").setInputFiles(FIXTURE);
      const uploaded = technician.page.waitForResponse(
        (response) =>
          response.url().endsWith("/api/v1/documents") &&
          response.request().method() === "POST",
      );
      await technician.page
        .getByRole("dialog")
        .getByRole("button", { name: "Upload PDF", exact: true })
        .click();
      const uploadResponse = await uploaded;
      expect(uploadResponse.status()).toBe(202);
      const document = (
        (await uploadResponse.json()) as {
          document: { id: number; status: string };
        }
      ).document;
      documentId = document.id;
      expect(["quarantined", "queued"]).toContain(document.status);
      await expect(
        technician.page.getByRole("heading", { name: "Manual received" }),
      ).toBeVisible();
      await technician.page
        .getByRole("button", { name: "Return to manuals" })
        .click();
      await expect
        .poll(
          async () => {
            const response = await technician.context.request.get(
              `/api/v1/documents/${documentId}`,
            );
            expect(response.status()).toBe(200);
            const result = (
              (await response.json()) as {
                document: { status: string; error?: string };
              }
            ).document;
            if (["failed", "blocked"].includes(result.status))
              throw new Error(
                `Actual PDF processing failed: ${result.error || result.status}`,
              );
            return result.status;
          },
          { timeout: 90000, intervals: [300, 700, 1500] },
        )
        .toBe("ready");
      await technician.page
        .getByRole("button", { name: "Refresh status" })
        .click();
      await technician.page
        .getByRole("button", { name: "Read manual", exact: true })
        .click();
      await expect(
        technician.page.getByRole("article", { name: "Manual page 1" }),
      ).toContainText("TEST-ONLY-42");
      await screenshot(
        technician.page,
        "technician-authenticated-manual-marker",
      );
      const pendingDownload = technician.page.waitForEvent("download");
      await technician.page
        .getByRole("dialog")
        .getByRole("button", { name: "Download PDF", exact: true })
        .click();
      const downloaded = await pendingDownload;
      expect(await downloaded.failure()).toBeNull();
      expect(downloaded.suggestedFilename()).toMatch(/\.pdf$/i);
      const stream = await downloaded.createReadStream();
      expect(stream).not.toBeNull();
      const chunks: Buffer[] = [];
      for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
      expect(Buffer.concat(chunks).subarray(0, 5).toString()).toBe("%PDF-");
      await technician.page
        .getByRole("button", { name: "Close dialog" })
        .click();
      await expect(
        technician.page.getByRole("button", {
          name: /Remove Test-only supplier manual/,
        }),
      ).toHaveCount(0);
    });

    await test.step("Stores and viewer accept real invitations but cannot perform registry, job, or manual writes", async () => {
      for (const role of ["stores", "viewer"] as const) {
        const person = await persona(
          browser,
          origin,
          `${role}-${stamp}@example.test`,
          `Test-only!${role}-${stamp}-42`,
        );
        people.push(person);
        if (role === "stores") stores = person;
        else viewer = person;
        await inviteFromWorkbench(administrator.page, person.email, role);
        await acceptAndLogin(person, `Test-only ${role} colleague`);
        await person.page.goto("/app/machines");
        await expect(
          person.page
            .getByRole("link", { name: /Test-only manual fixture pump/ })
            .first(),
        ).toBeVisible();
        await expect(
          person.page.getByRole("button", {
            name: "Record machine",
            exact: true,
          }),
        ).toHaveCount(0);
        await write(
          person.context.request,
          "/assets",
          { code: `DENIED-${role}-${stamp}`, name: "Write must not persist" },
          403,
        );
        await person.page.goto("/app/maintenance");
        await expect(
          person.page.getByRole("button", { name: "Create job", exact: true }),
        ).toHaveCount(0);
        await write(
          person.context.request,
          "/work-orders",
          { asset_id: machineId, title: "Denied role request" },
          403,
        );
        await person.page.goto(`/app/manuals?asset_id=${machineId}`);
        await expect(
          person.page.getByRole("button", { name: "Upload PDF", exact: true }),
        ).toHaveCount(0);
        await expect(
          person.page.getByRole("button", { name: "Read manual", exact: true }),
        ).toBeVisible();
        await write(
          person.context.request,
          `/documents/${documentId}`,
          {},
          403,
          "DELETE",
        );
        await person.page.setViewportSize({ width: 390, height: 844 });
        await screenshot(person.page, `${role}-read-only-manuals-mobile`);
        expect(
          await person.page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth,
          ),
        ).toBe(true);
      }
      expect(stores.email).not.toBe(viewer.email);
    });

    await test.step("A foreign owner cannot read private manual text or downloads, even via a guessed URL", async () => {
      foreign = await owner(browser, origin, stamp, "foreign");
      people.push(foreign);
      for (const suffix of ["", "/pages/1", "/download"]) {
        const denied = await foreign.context.request.get(
          `/api/v1/documents/${documentId}${suffix}`,
        );
        expect([403, 404]).toContain(denied.status());
        expect(await denied.text()).not.toContain("TEST-ONLY-42");
      }
      await foreign.page.goto(`/app/manuals?document=${documentId}`);
      await expect(
        foreign.page.getByRole("dialog").getByRole("alert"),
      ).toContainText("not found");
      await expect(
        foreign.page.getByRole("article", { name: "Manual page 1" }),
      ).toHaveCount(0);
      await screenshot(foreign.page, "foreign-owner-private-manual-denied");
      await foreign.page.getByRole("button", { name: "Close dialog" }).click();
    });

    await test.step("The foreign owner accepts an existing-account invitation and switches tenant without carrying cached manual data", async () => {
      await inviteFromWorkbench(administrator.page, foreign.email, "viewer");
      const invitation = new URL(
        await waitForMailLink(
          foreign.context.request,
          foreign.email,
          "/invite",
        ),
      );
      await foreign.page.goto(invitation.pathname + invitation.search);
      await expect(foreign.page.getByLabel("Create password")).toHaveCount(0);
      await foreign.page
        .getByRole("button", { name: "Accept invitation" })
        .click();
      await expect(foreign.page.getByRole("status")).toContainText(
        "Invitation accepted",
      );
      await foreign.page
        .getByRole("link", { name: "Open workbench", exact: true })
        .click();
      await foreign.page
        .getByLabel("Switch organization")
        .selectOption(String(administrator.companyId));
      await foreign.page
        .getByRole("button", { name: "Switch organization", exact: true })
        .click();
      await expect(
        foreign.page
          .getByRole("definition")
          .filter({ hasText: "viewer" })
          .first(),
      ).toBeVisible();
      await foreign.page.goto(`/app/manuals?asset_id=${machineId}`);
      await foreign.page
        .getByRole("button", { name: "Read manual", exact: true })
        .click();
      await expect(
        foreign.page.getByRole("article", { name: "Manual page 1" }),
      ).toContainText("TEST-ONLY-42");
      await foreign.page.getByRole("button", { name: "Close dialog" }).click();
      await foreign.page.goto("/app/team");
      await foreign.page
        .getByLabel("Switch organization")
        .selectOption(String(foreign.companyId));
      const switchBack = foreign.page.waitForResponse((response) => response.url().endsWith('/api/v1/companies/switch') && response.request().method() === 'POST');
      await foreign.page.getByRole("button", { name: "Switch organization", exact: true }).click();
      expect((await switchBack).status()).toBe(200);
      await expect.poll(async () => (await foreign.context.request.get('/api/v1/auth/me')).json()).toMatchObject({company: {id: foreign.companyId}});
      await foreign.page.goto("/app/manuals");
      await expect(
        foreign.page.getByText("Instructions belong with the machine", {
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        foreign.page.getByText("Test-only supplier manual TEST-ONLY-42", {
          exact: true,
        }),
      ).toHaveCount(0);
      const denied = await foreign.context.request.get(
        `/api/v1/documents/${documentId}/download`,
      );
      expect([403, 404]).toContain(denied.status());
      await screenshot(
        foreign.page,
        "organization-switch-clears-private-manuals",
      );
    });
  } finally {
    await Promise.all(people.map((person) => person.context.close()));
  }
});
