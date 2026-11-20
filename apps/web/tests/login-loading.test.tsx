import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import { withTimeout } from "@/lib/http";
import LoginPage from "../app/login/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/login",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const problem = (status: number, code: string) => ({ type: "x", title: "t", status, code });
const res = (status: number) => new Response(null, { status });

type Init = { signal?: AbortSignal };
/** /v1/me -> 401 (not signed in). /v1/auth/config -> chosen behaviour; "hang" answers only when the request is aborted. */
function stubApi(config: "ok" | "500" | "hang" | "throws") {
  vi.spyOn(api, "GET").mockImplementation(((path: string, init?: Init) => {
    if (path === "/v1/me") return Promise.resolve({ error: problem(401, "UNAUTHENTICATED"), response: res(401) });
    if (config === "ok") return Promise.resolve({ data: { guestEnabled: false }, response: res(200) });
    if (config === "500") return Promise.resolve({ error: problem(500, "INTERNAL"), response: res(500) });
    if (config === "throws") return Promise.reject(new TypeError("Extension broke fetch"));
    return new Promise((_, reject) => init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))));
  }) as never);
}

function renderLogin() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const form = () => screen.queryByRole("textbox", { name: "Email hoặc mã học sinh" });
const guestButton = () => screen.queryByRole("button", { name: "Vào làm thử (không cần tài khoản)" });

it("/v1/me 401 means 'not signed in': the form shows as soon as the config answers", async () => {
  stubApi("ok");
  renderLogin();
  expect(await screen.findByRole("textbox", { name: "Email hoặc mã học sinh" })).toBeTruthy();
  expect(screen.queryByText(/Máy chủ đang khởi động/)).toBeNull(); // 401 is not an error state
  expect(guestButton()).toBeNull();
});

it("config 500: form stays, guest button hidden, 'server is starting' notice with a retry button", async () => {
  stubApi("500");
  renderLogin();
  expect(await screen.findByText(/Máy chủ đang khởi động/)).toBeTruthy();
  expect(form()).toBeTruthy();
  expect(guestButton()).toBeNull();
  expect(screen.getByRole("button", { name: "Thử lại" })).toBeTruthy();
});

it("config answering after 30 s: form after 3 s, error state at the 15 s timeout, never an endless spinner", async () => {
  stubApi("hang");
  renderLogin();
  expect(screen.getByText("Đang tải…")).toBeTruthy(); // first seconds: brief spinner only
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3_200);
  });
  expect(form()).toBeTruthy(); // the account form is usable while the config is slow
  expect(screen.getByText(/Đang kiểm tra chế độ vào làm thử/)).toBeTruthy();
  expect(screen.queryByText(/Máy chủ đang khởi động/)).toBeNull();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(12_500); // 15 s: the config request is aborted by its timeout
  });
  expect(await screen.findByText(/Máy chủ đang khởi động/)).toBeTruthy();
  expect(screen.queryByText("Đang tải…")).toBeNull();
  expect(form()).toBeTruthy();
  expect(guestButton()).toBeNull();
});

it("a browser extension that breaks fetch does not break the page", async () => {
  stubApi("throws");
  renderLogin();
  expect(await screen.findByText(/Máy chủ đang khởi động/)).toBeTruthy();
  expect(form()).toBeTruthy();
});

it("withTimeout aborts after the delay, or earlier with the outer signal", async () => {
  const slow = withTimeout(1_000);
  expect(slow.aborted).toBe(false);
  await vi.advanceTimersByTimeAsync(1_100);
  expect(slow.aborted).toBe(true);
  const outer = new AbortController();
  const linked = withTimeout(60_000, outer.signal);
  outer.abort();
  expect(linked.aborted).toBe(true);
});
