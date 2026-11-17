import path from "node:path";
import type { NextConfig } from "next";

const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

const config: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
  transpilePackages: ["@preclass/api-client"],
  poweredByHeader: false,
  // Dev only: production serves /v1 from the same origin through Caddy, which routes /v1/* to the API first.
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${apiOrigin}/v1/:path*` }];
  },
};

export default config;
