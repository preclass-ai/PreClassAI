import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  plugins: [react()],
  resolve: {
    alias: {
      "@preclass/api-client": fileURLToPath(new URL("../../packages/api-client/src/index.ts", import.meta.url)),
    },
  },
  server: { proxy: { "/v1": "http://127.0.0.1:8000", "/mock": { target: "http://127.0.0.1:4010", rewrite: (p) => p.replace(/^\/mock/, "") } } },
});
