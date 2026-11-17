import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  esbuild: { jsx: "automatic" },
  test: { environment: "jsdom", include: ["tests/**/*.test.{ts,tsx}"], exclude: ["tests/e2e/**", "node_modules/**"], setupFiles: ["tests/setup.ts"] },
});
