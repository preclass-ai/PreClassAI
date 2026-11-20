import { createApiClient, isProblem, type Problem, type Schemas } from "@preclass/api-client";
import { timeoutFetch } from "./http";

export type { Problem, Schemas };

/** Same-origin client: cookie session + `X-PreClass-CSRF: 1` are sent on every request. */
export const api = createApiClient({ fetch: timeoutFetch });

/** A failed API call. Branch on `code` (stable), never on `title`/`detail` (Vietnamese text, may change). */
export class ApiError extends Error {
  readonly problem: Problem;

  constructor(problem: Problem) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.problem = problem;
  }

  get code(): string {
    return this.problem.code;
  }

  get status(): number {
    return this.problem.status;
  }

  get blockIds(): string[] {
    const ids = this.problem.blockIds;
    return Array.isArray(ids) ? ids.filter((x): x is string => typeof x === "string") : [];
  }
}

function fallbackProblem(status: number, code: string, title: string): Problem {
  return { type: "about:blank", title, detail: title, status, code };
}

let onUnauthenticated: (() => void) | null = null;

/** Registered by the auth provider: a 401 anywhere sends the user back to login. */
export function setUnauthenticatedHandler(fn: (() => void) | null): void {
  onUnauthenticated = fn;
}

interface Result<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Awaits an openapi-fetch call and returns its data, or throws `ApiError` with the RFC 9457 problem. */
export async function unwrap<T>(call: Promise<Result<T>>, opts: { quiet401?: boolean } = {}): Promise<T> {
  let res: Result<T>;
  try {
    res = await call;
  } catch {
    throw new ApiError(fallbackProblem(0, "NETWORK", "Không kết nối được máy chủ"));
  }
  if (res.error !== undefined || !res.response.ok) {
    const problem = isProblem(res.error)
      ? res.error
      : fallbackProblem(res.response.status, "UNKNOWN", `Lỗi máy chủ (${res.response.status})`);
    if (problem.status === 401 && !opts.quiet401) onUnauthenticated?.();
    throw new ApiError(problem);
  }
  return res.data as T;
}

/** Multipart upload (DOCX). openapi-fetch would JSON-encode the body, so this uses fetch directly. */
export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const call = fetch(path, {
    method: "POST",
    body: form,
    credentials: "include",
    headers: { "X-PreClass-CSRF": "1" },
  }).then(async (response) => {
    const body: unknown = response.status === 204 ? undefined : await response.json().catch(() => undefined);
    return response.ok ? { data: body as T, response } : { error: body, response };
  });
  return unwrap<T>(call);
}
