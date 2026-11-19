import { expect, type Page } from "@playwright/test";

export const PASSWORD = process.env.SEED_PASSWORD ?? "preclass-demo";

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
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  // Generous: the first hit on a dev server compiles the target route.
  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });
}

/** No horizontal page scroll at any viewport (tables scroll inside their own wrapper). */
export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}
