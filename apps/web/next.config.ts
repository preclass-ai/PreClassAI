import path from "node:path";
import type { NextConfig } from "next";

const isDeploy = process.env.VERCEL === "1" || process.env.NODE_ENV === "production";

/** A deploy must point /v1 at a public https API: localhost/private hosts made Vercel answer DNS_HOSTNAME_RESOLVED_PRIVATE. */
function resolveApiOrigin(): string {
  const raw = process.env.API_ORIGIN?.trim();
  // ALLOW_LOCAL_API_ORIGIN=1: local production build for E2E against a local API. Never honoured on Vercel.
  const local = process.env.VERCEL !== "1" && process.env.ALLOW_LOCAL_API_ORIGIN === "1";
  if (!isDeploy || local) return raw || "http://localhost:8000";
  if (!raw) throw new Error("API_ORIGIN is required for a production/Vercel build (e.g. https://preclass-api.onrender.com).");
  const host = new URL(raw).hostname;
  const privateHost = /^(localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|0\.0\.0\.0|\[?::1\]?$)/;
  if (privateHost.test(host) || host.endsWith(".local") || host.endsWith(".internal")) {
    throw new Error(`API_ORIGIN must be a public host, got "${raw}".`);
  }
  return raw.replace(/\/+$/, "");
}

const apiOrigin = resolveApiOrigin();

/**
 * Security headers for every page. script-src keeps 'unsafe-inline' because Next injects inline bootstrap scripts and a
 * nonce would turn every statically rendered page into a dynamic one (tracked in docs/security). No 'unsafe-eval' in
 * production (React dev tooling needs it only in `next dev`). /docs is the API's Scalar page (CDN script): no CSP there.
 */
const dev = process.env.NODE_ENV !== "production";
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");
const baseHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const config: NextConfig = {
  // Vercel has its own output format; standalone is for the Docker image only.
  ...(process.env.VERCEL ? {} : { output: "standalone" as const }),
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
  transpilePackages: ["@preclass/api-client"],
  poweredByHeader: false,
  distDir: process.env.NEXT_DIST_DIR ?? ".next", // lets CI/ops build without touching a running `next start`
  async headers() {
    return [
      { source: "/((?!docs).*)", headers: [...baseHeaders, { key: "Content-Security-Policy", value: csp }] },
      { source: "/docs", headers: baseHeaders },
    ];
  },
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
