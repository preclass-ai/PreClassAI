import { defineConfig, devices } from "@playwright/test";

// Release E2E against a deployed URL (tunnel or cloud). Env: E2E_BASE_URL, SEED_PASSWORD, optional PREVIEW_USER/PREVIEW_PASS (basic auth).
export default defineConfig({
  testDir: "tests/release-1911",
  outputDir: "test-results/pw-output-1911",
  timeout: 300_000,
  workers: 1,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL,
    locale: "vi-VN",
    trace: "retain-on-failure",
    launchOptions: { executablePath: process.env.CHROMIUM_PATH },
    ...(process.env.PREVIEW_USER
      ? { httpCredentials: { username: process.env.PREVIEW_USER, password: process.env.PREVIEW_PASS ?? "", send: "always" as const } }
      : {}),
  },
  projects: [
    { name: "390", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } } },
    { name: "768", use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } } },
    { name: "1280", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    // Safari on iPhone (required for the cloud acceptance run).
    { name: "webkit", use: { ...devices["iPhone 13"], launchOptions: {} } },
  ],
});
