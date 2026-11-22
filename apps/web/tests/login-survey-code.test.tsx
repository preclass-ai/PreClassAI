import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import LoginPage from "../app/login/page";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/login",
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(),
}));

const problem = (status: number, code: string) => ({ type: "x", title: "t", status, code });
const res = (status: number) => new Response(null, { status });

function stub(resume: "ok" | "404" | "429") {
  vi.spyOn(api, "GET").mockImplementation(((path: string) =>
    path === "/v1/me"
      ? Promise.resolve({ error: problem(401, "UNAUTHENTICATED"), response: res(401) })
      : Promise.resolve({ data: { guestEnabled: true }, response: res(200) })) as never);
  return vi.spyOn(api, "POST").mockImplementation(((path: string) => {
    if (path !== "/v1/auth/guest/resume") return Promise.reject(new Error(`unexpected ${path}`));
    if (resume === "404") return Promise.resolve({ error: problem(404, "NOT_FOUND"), response: res(404) });
    if (resume === "429") return Promise.resolve({ error: problem(429, "RATE_LIMITED"), response: res(429) });
    const user = { id: "u", role: "STUDENT", displayName: "Khách ABCD", isGuest: true, surveyCode: "KS-ABCD" };
    return Promise.resolve({ data: { user }, response: res(200) });
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

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  replace.mockReset();
});

async function typeCodeAndPressEnter(code: string) {
  const input = await screen.findByRole("textbox", { name: /Mã khảo sát/ });
  fireEvent.change(input, { target: { value: code } });
  fireEvent.submit(input.closest("form")!); // what Enter in the field does
  return input;
}

it("Enter in the survey-code field resumes the guest instead of submitting the collapsed account form", async () => {
  const post = stub("ok");
  renderLogin();
  await typeCodeAndPressEnter("KS-ABCD");
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/student"));
  expect(post).toHaveBeenCalledWith("/v1/auth/guest/resume", { body: { surveyCode: "KS-ABCD" } });
  expect(post).not.toHaveBeenCalledWith("/v1/auth/login", expect.anything());
});

it("the survey code and the account fields are separate forms", async () => {
  stub("ok");
  renderLogin();
  const code = await screen.findByRole("textbox", { name: /Mã khảo sát/ });
  const identifier = screen.getByRole("textbox", { name: "Email hoặc mã học sinh" });
  expect(code.closest("form")).not.toBe(identifier.closest("form"));
});

it("a wrong code is reported next to the field, not as the generic 'not found' alert", async () => {
  stub("404");
  renderLogin();
  const input = await typeCodeAndPressEnter("KS-0000");
  expect(await screen.findByText(/Mã khảo sát không đúng/)).toBeTruthy();
  expect(input.getAttribute("aria-invalid")).toBe("true");
  expect(input.getAttribute("aria-describedby")).toBe("survey-code-error");
  expect(screen.queryByText(/Không tìm thấy, hoặc tài khoản/)).toBeNull();
  fireEvent.change(input, { target: { value: "KS-0001" } }); // editing clears the error
  expect(screen.queryByText(/Mã khảo sát không đúng/)).toBeNull();
  expect(input.getAttribute("aria-invalid")).toBeNull();
});

it("other errors (rate limit) still use the shared error box", async () => {
  stub("429");
  renderLogin();
  await typeCodeAndPressEnter("KS-0000");
  expect(await screen.findByText(/quá nhiều lần/)).toBeTruthy();
  expect(screen.queryByText(/Mã khảo sát không đúng/)).toBeNull();
});
