import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, login } from "./helpers";

const STUDENT: Record<string, string> = { "mobile-390": "HS10-03", "tablet-768": "HS10-04", "desktop-1280": "HS10-05" };

test("student answers first, then sees the approved explanation", async ({ page }, info) => {
  await login(page, STUDENT[info.project.name] ?? "HS10-06");
  await expect(page.getByRole("heading", { name: "Bài được giao" })).toBeVisible();
  await page.locator(".assignment-card").first().click();
  await expect(page).toHaveURL(/\/student\/assignments\//);
  await expect(page.locator("section.item").first()).toBeVisible();
  await expectNoHorizontalScroll(page);

  // Pin the item by id: after answering, its options are replaced by the result.
  const open = page.locator("section.item").filter({ has: page.locator(".options") }).first();
  const item = (await open.count())
    ? page.locator(`section[aria-labelledby="${await open.getAttribute("aria-labelledby")}"]`)
    : page.locator("section.item").first();
  if (await item.getByRole("button", { name: "Nộp câu trả lời" }).count()) {
    // No explanation before answering.
    await expect(item.locator(".explanation")).toHaveCount(0);
    await item.locator(".option").first().click();
    await item.getByRole("button", { name: "Nộp câu trả lời" }).click();
  }
  await expect(item.getByRole("status")).toContainText(/Đúng|Chưa đúng/);
  await expect(item.locator(".explanation")).not.toBeEmpty();
  await page.screenshot({ path: `test-results/screens/student-${info.project.name}.png`, fullPage: true });
});
