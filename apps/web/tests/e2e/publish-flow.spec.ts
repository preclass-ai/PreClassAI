import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// Changes data (adds a revision to the seeded lesson each run): desktop only, dev/staging seed only.
test("new revision → approve block by block → publish → assign (S04–S06)", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1280", "write flow runs once");
  page.on("dialog", (d) => void d.accept());
  await login(page, "gv.dia@preclass.local");
  await page.getByRole("link", { name: "Phân bố dân cư theo vùng" }).click();

  // S06: a published revision is locked; editing starts a new draft without carrying approvals.
  await page.getByRole("tab", { name: "Lịch sử" }).click();
  const newRev = page.getByRole("button", { name: "Tạo bản sửa mới" });
  if (await newRev.count()) await newRev.click();
  await expect(page.getByText("Bản nháp").first()).toBeVisible();

  // S04: approve each block individually (there is no "approve all").
  await page.getByRole("tab", { name: "Duyệt" }).click();
  const approve = page.getByRole("button", { name: "Duyệt khối này" });
  await expect(approve.first()).toBeVisible();
  // The queue re-renders after every decision, so a click can land on a card that is replaced a moment later and be lost
  // (no error on screen, the "x/y đã duyệt" counter does not move). Click again until the queue is empty.
  for (let i = 0; i < 80 && (await approve.count()) > 0; i++) {
    const before = await approve.count();
    await approve.first().click();
    await expect.poll(() => approve.count(), { timeout: 4_000 }).toBeLessThan(before).catch(() => undefined);
  }
  await expect(approve).toHaveCount(0);

  // S05: gate passes, explicit confirmation, publish, then assign to a class of the same grade.
  await page.getByRole("tab", { name: /Xuất bản/ }).click();
  await expect(page.locator(".checklist li.fail")).toHaveCount(0);
  await page.getByText("Tôi đã đọc từng khối").click();
  await page.getByRole("button", { name: "Xuất bản", exact: true }).click();
  await expect(page.getByText(/đã xuất bản\./)).toBeVisible();
  await page.getByRole("button", { name: "Giao bài" }).click();
  await expect(page.getByText(/Đã giao cho lớp/)).toBeVisible();

  // S06: the published snapshot can be opened read-only from the history.
  await page.getByRole("tab", { name: "Lịch sử" }).click();
  await page.getByRole("button", { name: /^Xem bản #/ }).first().click();
  await expect(page.locator(".tree.snapshot .block-card").first()).toBeVisible();
});
