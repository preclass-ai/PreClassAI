import { defineConfig, devices } from "@playwright/test";

/**
 * E2E against a running stack: API on :8000 (seeded dev DB, COOKIE_SECURE=false) and `pnpm dev` on :3000.
 * Override with E2E_BASE_URL. Tests change data (reviews, answers), so run them on a dev/staging seed only.
 */
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", trace: "retain-on-failure", locale: "vi-VN" },
  projects: [
    { name: "mobile-390", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } } },
    { name: "tablet-768", use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } } },
    { name: "desktop-1280", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    // Opt-in (needs `npx playwright install webkit`): E2E_WEBKIT=1
    ...(process.env.E2E_WEBKIT ? [{ name: "webkit-390", use: { ...devices["iPhone 13"], viewport: { width: 390, height: 844 } } }] : []),
  ],
});
