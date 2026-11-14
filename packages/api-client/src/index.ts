import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type { components, paths };
export type Schemas = components["schemas"];

/** RFC 9457 problem details returned by every non-2xx response. Branch on `code`, never on `title`. */
export type Problem = Schemas["Problem"];

export interface ClientOptions {
  /** "" = same origin (production Caddy, dev rewrites). */
  baseUrl?: string;
  fetch?: typeof fetch;
}

/**
 * Thin typed client. Sends the session cookie (`credentials: "include"`) and the CSRF header the API
 * requires on every non-GET request.
 */
export function createApiClient(opts: ClientOptions = {}) {
  return createClient<paths>({
    baseUrl: opts.baseUrl ?? "",
    credentials: "include",
    headers: { "X-PreClass-CSRF": "1" },
    ...(opts.fetch ? { fetch: opts.fetch } : {}),
  });
}

export type ApiClient = ReturnType<typeof createApiClient>;

export function isProblem(e: unknown): e is Problem {
  return typeof e === "object" && e !== null && "code" in e && "status" in e;
}
