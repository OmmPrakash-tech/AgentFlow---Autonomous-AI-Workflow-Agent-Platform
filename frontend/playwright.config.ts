import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.e2e.ts",
  workers: 1,
  reporter: "list",
  outputDir: "../work/final-verification/browser-results",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5174",
    channel: process.env.E2E_BROWSER_CHANNEL || "msedge",
    headless: true,
    trace: "off",
    screenshot: "only-on-failure",
  },
});
