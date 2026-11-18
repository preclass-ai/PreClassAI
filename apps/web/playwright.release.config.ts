import { defineConfig, devices } from "@playwright/test";

// Release 19/11 E2E through the tunnel. Env: E2E_BASE_URL, PREVIEW_USER, PREVIEW_PASS (basic auth), SEED_PASSWORD.
export default defineConfig({
  testDir: "tests/release-1911",
  outputDir: "test-results/pw-output-1911",
  timeout: 180_000,
  workers: 1,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL,
    locale: "vi-VN",
    launchOptions: { executablePath: process.env.CHROMIUM_PATH },
    httpCredentials: { username: process.env.PREVIEW_USER ?? "", password: process.env.PREVIEW_PASS ?? "", send: "always" },
  },
  projects: [
    { name: "390", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } } },
    { name: "768", use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } } },
    { name: "1280", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
  ],
});
