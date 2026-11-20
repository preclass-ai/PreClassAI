import { expect, type Page } from "@playwright/test";

export const PASSWORD = process.env.SEED_PASSWORD ?? "preclass-demo";

/** Cloud E2E runs against a deployed demo: no shared password. Teacher: E2E_TEACHER_PASSWORD (set in your shell for the
 * session, never stored); E2E student "E2E-1": E2E_STUDENT_PASSWORD; admin: SEED_ADMIN_PASSWORD. Each falls back to the
 * older SEED_* variables, then SEED_PASSWORD, then the local dev default. */
export function passwordFor(identifier: string): string {
  const id = identifier.toLowerCase();
  if (id.startsWith("admin@")) return process.env.SEED_ADMIN_PASSWORD ?? PASSWORD;
  if (id.startsWith("e2e-")) return process.env.E2E_STUDENT_PASSWORD ?? PASSWORD;
  if (id.startsWith("hs")) return process.env.SEED_STUDENT_PASSWORD ?? PASSWORD;
  return process.env.E2E_TEACHER_PASSWORD ?? process.env.SEED_TEACHER_PASSWORD ?? PASSWORD;
}

/** E2E mode (cloud): lessons are assigned to the private class "E2E" and answered by the student E2E-1. Guests never see them. */
export const E2E_MODE = !!process.env.E2E_STUDENT_PASSWORD;
export const E2E_CLASS_LABEL = E2E_MODE ? "E2E" : "10A1";
export const TITLE_PREFIX = "[E2E] ";

/** With guest access on, the account form is collapsed under "Giáo viên / có tài khoản": open it when present. */
export async function openAccountForm(page: Page) {
  const toggle = page.getByText("Giáo viên / có tài khoản");
  await expect(toggle.or(page.getByLabel("Email hoặc mã học sinh")).first()).toBeVisible({ timeout: 30_000 });
  if (await toggle.isVisible()) await toggle.click();
}

export async function login(page: Page, identifier: string) {
  await page.goto("/login");
  await openAccountForm(page);
  await page.getByLabel("Email hoặc mã học sinh").fill(identifier);
  await page.getByLabel("Mật khẩu").fill(passwordFor(identifier));
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  // Generous: the first hit on a dev server compiles the target route.
  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });
}

/** No horizontal page scroll at any viewport (tables scroll inside their own wrapper). */
export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}
