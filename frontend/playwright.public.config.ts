import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/public-e2e",
  outputDir: "public-test-results",
  workers: 1,
  timeout: 30000,
  reporter: "list",
  use: {
    baseURL: process.env.PDM_PUBLIC_URL || "http://localhost:5175",
    ...devices["Desktop Chrome"],
    channel: process.env.PDM_BROWSER_CHANNEL || "msedge",
    trace: "retain-on-failure",
  },
});
