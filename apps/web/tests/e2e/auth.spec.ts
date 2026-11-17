import { expect, test } from "@playwright/test";
import { login, PASSWORD } from "./helpers";

test("wrong password shows a message by error code", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email hoặc mã học sinh").fill("gv.dia@preclass.local");
  await page.getByLabel("Mật khẩu").fill(`${PASSWORD}-wrong`);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.locator(".alert[role=alert]")).toContainText("Sai tài khoản hoặc mật khẩu");
});

test("each role lands on its own home and cannot open teacher screens", async ({ page }) => {
  await login(page, "HS10-02");
  await expect(page).toHaveURL(/\/student$/);
  await page.goto("/lessons");
  await expect(page).toHaveURL(/\/student$/);
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/lessons");
  await expect(page).toHaveURL(/\/login\?next=%2Flessons/);
});
