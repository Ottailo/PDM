import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

test("public pilot has real disclosures, no private controls or API requests", async ({ page }) => {
  const errors: string[] = [];
  const apiRequests: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (new URL(request.url()).pathname.startsWith("/api")) apiRequests.push(request.url());
  });
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  await expect(page.getByText(/private pilot/i).first()).toBeVisible();
  await expect(page.locator("form, input, textarea, select")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /sign in|create account|upload/i })).toHaveCount(0);
  const details = page.locator("details").nth(1);
  await details.locator("summary").click();
  await expect(details).toHaveAttribute("open", "");
  await details.locator("summary").click();
  await expect(details).not.toHaveAttribute("open");
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true);
  await page.locator("h1").click();
  const directory = resolve("../tests/screenshots/public-pilot");
  await mkdir(directory, { recursive: true });
  await page.screenshot({ path: resolve(directory, "desktop.png"), fullPage: true });
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.locator("h1")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: resolve(directory, `mobile-${width}.png`), fullPage: true });
  }
  for (const pathname of ["/login", "/signup", "/app/machines", "/invite?token=not-a-real-token", "/mobile"]) {
    await page.goto(pathname);
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("form, input, textarea")).toHaveCount(0);
  }
  expect(apiRequests).toEqual([]);
  expect(errors).toEqual([]);
});

test("API requests cannot masquerade as working accounts or SPA HTML", async ({ request }) => {
  for (const pathname of ["/api", "/api/v1/auth/me", "/api/v1/documents/1/download"]) {
    const response = await request.get(pathname);
    expect(response.status()).toBe(503);
    expect(response.headers()["cache-control"]).toBe("no-store");
    expect(response.headers()["content-type"]).toContain("application/json");
    expect((await response.json()).error.code).toBe("private_pilot_unavailable");
  }
  const response = await request.post("/api/v1/auth/signup", { data: { email: "test@example.test" } });
  expect(response.status()).toBe(503);
  expect((await response.json()).error.code).toBe("private_pilot_unavailable");
});
