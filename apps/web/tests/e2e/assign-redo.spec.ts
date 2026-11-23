import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, login } from "./helpers";

// Writes student data (answers) and only HS10-09 is free of other specs: runs once, on desktop.

test("student can redo a question for practice", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1280", "writes student data, runs once");
  await login(page, "HS10-09");
  await expect(page.getByRole("heading", { name: "Bài được giao" })).toBeVisible();

  await page.locator(".assignment-card").first().click();
  const open = page.locator("section.item").filter({ has: page.locator(".options") }).first();
  const id = await open.getAttribute("aria-labelledby");
  const item = page.locator(`section[aria-labelledby="${id}"]`);
  await item.locator(".option").first().click();
  await item.getByRole("button", { name: "Nộp câu trả lời" }).click();
  await expect(item.getByRole("status").first()).toContainText(/Đúng|Chưa đúng/);

  await item.getByRole("button", { name: "Làm lại" }).click();
  await expect(item.getByText(/Lượt luyện tập/)).toBeVisible();
  await item.locator(".option").last().click();
  await item.getByRole("button", { name: "Nộp lần làm lại" }).click();
  await expect(item.getByRole("status").filter({ hasText: "Lần làm lại" })).toBeVisible();
  await expect(item.getByRole("button", { name: "Làm lại" })).toBeVisible(); // as often as they like
  await expectNoHorizontalScroll(page);
});

test("teacher changes a due time and the lesson page says where it is assigned", async ({ page }) => {
  await login(page, "gv.dia@preclass.local");
  await page.goto("/classes");
  await expect(page.getByRole("link", { name: "Giao bài mới" })).toBeVisible();
  const card = page.locator("li.card").first();
  await card.getByRole("button", { name: "Sửa hạn" }).click();
  const due = new Date(Date.now() + 25 * 86_400_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  await card.getByLabel("Hạn nộp mới").fill(`${due.getFullYear()}-${pad(due.getMonth() + 1)}-${pad(due.getDate())}T23:59`);
  await card.getByRole("button", { name: "Lưu hạn" }).click();
  await expect(card.getByText(new RegExp(`hạn .*${due.getFullYear()}`))).toBeVisible();
  await card.getByRole("link", { name: "Mở bài học" }).click();
  await expect(page.getByText(/Đã giao cho:/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Hủy giao" })).toHaveCount(0); // cancelling lives on the class page
  await expectNoHorizontalScroll(page);
});
