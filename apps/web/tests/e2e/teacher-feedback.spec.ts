import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, login } from "./helpers";

// Teacher feedback (K1..K5). Read-only unless a test says otherwise.

test("K1: clicking an assignment in Lớp & bài giao opens that assignment's progress, not the lesson", async ({ page }) => {
  await login(page, "gv.dia@preclass.local");
  await page.goto("/classes");
  const card = page.locator("li.card").first();
  await expect(card).toBeVisible();
  const title = (await card.locator("h2").innerText()).trim();
  await card.locator("h2 a").click();
  await expect(page).toHaveURL(/\/classes\?.*assignment=/);
  await expect(page.locator("li.card").first().getByText(/em đã làm xong/).first()).toBeVisible();
  await expect(page.getByText(/Không tìm thấy|Có lỗi/)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: title }).first()).toBeVisible();
  await expectNoHorizontalScroll(page);
});
