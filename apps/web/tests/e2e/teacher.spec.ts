import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, login } from "./helpers";

test("teacher sees lessons, inspects a block's sources and the publish gate", async ({ page }, info) => {
  await login(page, "gv.dia@preclass.local");
  await expect(page).toHaveURL(/\/lessons$/);
  await expect(page.getByRole("heading", { name: "Bài học" })).toBeVisible();
  await expectNoHorizontalScroll(page);

  // A seeded draft lesson with blocks in several review states.
  const rows = page.locator("tbody tr").filter({ hasText: "Bản nháp" });
  await rows.first().getByRole("link").click();
  await expect(page.getByRole("tab", { name: "Soạn & nguồn" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: /Nội dung \(\d+ khối\)/ })).toBeVisible();

  // Selecting a block opens the Source Inspector with evidence, checks and history.
  await page.locator(".tree-node").filter({ hasText: /đoạn nguồn/ }).first().click();
  await expect(page.getByRole("heading", { name: "Nguồn" })).toBeVisible();
  await expect(page.locator(".evidence blockquote").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kiểm tra tự động" })).toBeVisible();
  // S03: review decisions sit next to the selected block, one block at a time.
  await expect(page.locator(".editor-inspector").getByRole("button", { name: "Duyệt khối này" })).toBeVisible();
  await expectNoHorizontalScroll(page);
  await page.screenshot({ path: `test-results/screens/editor-${info.project.name}.png`, fullPage: info.project.name !== "webkit-390" });
  // On mobile the inspector is a bottom sheet: close it before moving on.
  await page.getByRole("button", { name: "Đóng" }).click();
  await expect(page.locator(".editor-inspector.open")).toHaveCount(0);

  await page.getByRole("tab", { name: "Duyệt" }).click();
  await expect(page.getByText("Hiện khối")).toBeVisible();
  await expectNoHorizontalScroll(page);
  await page.screenshot({ path: `test-results/screens/review-${info.project.name}.png`, fullPage: info.project.name !== "webkit-390" });

  await page.getByRole("tab", { name: /Xuất bản/ }).click();
  await expect(page.getByRole("heading", { name: "Kiểm tra trước khi xuất bản" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Xuất bản", exact: true })).toBeDisabled();
  await page.screenshot({ path: `test-results/screens/publish-${info.project.name}.png`, fullPage: info.project.name !== "webkit-390" });
});

test("source library lists anchors of a source", async ({ page }) => {
  await login(page, "gv.dia@preclass.local");
  await page.getByRole("link", { name: "Nguồn", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Thư viện nguồn" })).toBeVisible();
  await page.locator("tbody tr a").first().click();
  await expect(page.getByRole("heading", { name: /Đoạn nguồn \(bản v\d+\)/ })).toBeVisible();
  await expect(page.locator("td.mono").first()).toBeVisible();
  await expectNoHorizontalScroll(page);
});
