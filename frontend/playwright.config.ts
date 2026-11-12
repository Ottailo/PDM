import { defineConfig, devices } from "@playwright/test";
// Servers are started by the local preview coordinator, never by this test runner.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 10000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PDM_E2E_URL || "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...(process.env.PDM_BROWSER_CHANNEL
      ? { channel: process.env.PDM_BROWSER_CHANNEL }
      : {}),
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
