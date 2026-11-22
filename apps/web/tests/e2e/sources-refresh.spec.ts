import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("S01: nguồn mới hiện ngay trong danh sách sau Lưu nguồn", async ({ page }) => {
  await login(page, "gv.dia@preclass.local");
  await page.goto("/sources");
  await expect(page.getByRole("table")).toBeVisible();
  const title = `Nguồn thử ${Date.now()}`;
  await page.getByRole("button", { name: "Thêm nguồn" }).click();
  await page.getByLabel("Tên nguồn").fill(title);
  await page.getByLabel("Nội dung").fill("Đoạn một.\n\nĐoạn hai.");
  await page.getByRole("button", { name: "Lưu nguồn" }).click();
  await expect(page.getByRole("link", { name: title })).toBeVisible({ timeout: 10_000 });
});
