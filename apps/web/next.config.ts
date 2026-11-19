import path from "node:path";
import type { NextConfig } from "next";

const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

const config: NextConfig = {
  // Vercel has its own output format; standalone is for the Docker image only.
  ...(process.env.VERCEL ? {} : { output: "standalone" as const }),
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
  transpilePackages: ["@preclass/api-client"],
  poweredByHeader: false,
  distDir: process.env.NEXT_DIST_DIR ?? ".next", // lets CI/ops build without touching a running `next start`
  // Dev and Vercel: one origin, the browser never calls the API host. Docker/prod: Caddy routes /v1/* first.
  async rewrites() {
    return [
      { source: "/v1/:path*", destination: `${apiOrigin}/v1/:path*` },
      { source: "/docs", destination: `${apiOrigin}/docs` },
      { source: "/openapi.json", destination: `${apiOrigin}/openapi.json` },
    ];
  },
};

export default config;
