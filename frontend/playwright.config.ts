import { defineConfig, devices } from "@playwright/test";

// Step 4 full-integration E2E suite — runs against the real Next.js dev
// server, the real Django backend, real PostgreSQL, and real Mailpit. No
// mocks. See e2e/global-setup.ts for the fixtures it depends on.
//
// Serial execution is deliberate: the backend enforces real throttles
// (5 ticket submissions/hour, 3 resend-link/hour) and the suite shares one
// Mailpit inbox and one admin session store, so tests are written as one
// coherent journey per file rather than isolated, parallel-safe units.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  globalSetup: require.resolve("./e2e/global-setup.ts"),
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
