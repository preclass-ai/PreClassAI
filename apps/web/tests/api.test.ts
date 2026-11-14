import { describe, expect, it, vi } from "vitest";
import { ApiError, setUnauthenticatedHandler, unwrap } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

const res = (status: number) => new Response(null, { status });

describe("unwrap", () => {
  it("returns data on success", async () => {
    await expect(unwrap(Promise.resolve({ data: { ok: 1 }, response: res(200) }))).resolves.toEqual({ ok: 1 });
  });

  it("throws ApiError carrying the problem code and blockIds", async () => {
    const problem = { type: "x", title: "t", status: 409, code: "PUBLISH_BLOCKED", blockIds: ["b1"] };
    const err = await unwrap(Promise.resolve({ error: problem, response: res(409) })).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe("PUBLISH_BLOCKED");
    expect((err as ApiError).blockIds).toEqual(["b1"]);
  });

  it("maps a rejected fetch to a NETWORK error", async () => {
    const err = await unwrap(Promise.reject(new TypeError("fetch failed"))).catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("NETWORK");
  });

  it("calls the 401 handler unless quiet", async () => {
    const handler = vi.fn();
    setUnauthenticatedHandler(handler);
    const p = { type: "x", title: "t", status: 401, code: "UNAUTHENTICATED" };
    await unwrap(Promise.resolve({ error: p, response: res(401) })).catch(() => undefined);
    await unwrap(Promise.resolve({ error: p, response: res(401) }), { quiet401: true }).catch(() => undefined);
    expect(handler).toHaveBeenCalledTimes(1);
    setUnauthenticatedHandler(null);
  });
});

describe("errorMessage", () => {
  it("uses the code, not the server's title", () => {
    const err = new ApiError({ type: "x", title: "server text", detail: "server text", status: 409, code: "STALE_REVIEW" });
    expect(errorMessage(err)).toMatch(/đã thay đổi/);
  });

  it("falls back to the server detail for unknown codes", () => {
    const err = new ApiError({ type: "x", title: "t", detail: "chi tiết", status: 400, code: "SOMETHING_NEW" });
    expect(errorMessage(err)).toBe("chi tiết");
  });
});
