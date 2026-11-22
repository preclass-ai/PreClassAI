import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api";
import { AuthProvider, ME_KEY } from "@/lib/auth";
import LoginPage from "../app/login/page";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/lessons",
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  replace.mockClear();
});

it("keeps the user signed in and shows an error when logout cannot reach the server", async () => {
  const user = {
    id: "00000000-0000-0000-0000-000000000001",
    role: "TEACHER",
    displayName: "Teacher One",
    email: "teacher@example.test",
    loginCode: null,
    classIds: [],
  };
  vi.spyOn(api, "POST").mockRejectedValue(new TypeError("Network unavailable"));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(ME_KEY, user);
  render(
    <QueryClientProvider client={client}>
      <AuthProvider><AppShell>Lesson</AppShell></AuthProvider>
    </QueryClientProvider>,
  );

  await screen.findByText("Teacher One");
  fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Không kết nối được máy chủ"));
  expect(screen.getByText("Teacher One")).toBeInTheDocument();
  expect(replace).not.toHaveBeenCalledWith("/login");
});

it("offers a keyboard shortcut past the main navigation", () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(ME_KEY, null);
  client.setQueryData(["auth-config"], { guestEnabled: false });
  render(
    <QueryClientProvider client={client}>
      <AuthProvider><AppShell>Lesson</AppShell></AuthProvider>
    </QueryClientProvider>,
  );
  expect(screen.getByRole("link", { name: "Bỏ qua điều hướng" })).toHaveAttribute("href", "#main-content");
  expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
});

it("names both login controls for browser form handling", () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(ME_KEY, null);
  client.setQueryData(["auth-config"], { guestEnabled: false });
  render(
    <QueryClientProvider client={client}>
      <AuthProvider><LoginPage /></AuthProvider>
    </QueryClientProvider>,
  );
  expect(screen.getByRole("textbox", { name: "Email hoặc mã học sinh" })).toHaveAttribute("name", "identifier");
  expect(screen.getByLabelText("Mật khẩu")).toHaveAttribute("name", "password");
});

it("login form never falls back to GET (the password must not end up in the URL)", () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(ME_KEY, null);
  client.setQueryData(["auth-config"], { guestEnabled: false });
  const { container } = render(
    <QueryClientProvider client={client}>
      <AuthProvider><LoginPage /></AuthProvider>
    </QueryClientProvider>,
  );
  expect(container.querySelector("form")).toHaveAttribute("method", "post");
});

it("with guest access on: a big guest button first, the account form collapsed below", () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(ME_KEY, null);
  client.setQueryData(["auth-config"], { guestEnabled: true });
  const { container } = render(
    <QueryClientProvider client={client}>
      <AuthProvider><LoginPage /></AuthProvider>
    </QueryClientProvider>,
  );
  expect(screen.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" })).toBeTruthy();
  expect(screen.getByText(/không hỏi tên hay email/)).toBeTruthy();
  const details = container.querySelectorAll("details.login-more");
  expect(details.length).toBe(2);
  details.forEach((d) => expect(d.hasAttribute("open")).toBe(false));
});
