import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// Changes data (adds a revision to the seeded lesson each run): desktop only, dev/staging seed only.
test("new revision → approve block by block → publish → assign (S04–S06)", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1280", "write flow runs once");
  test.setTimeout(240_000); // approving block by block takes about 30 s on a fresh seed and longer after the other specs added revisions
  page.on("dialog", (d) => void d.accept());
  await login(page, "gv.dia@preclass.local");
  await page.getByRole("link", { name: "Phân bố dân cư theo vùng" }).click();

  // S06: a published revision is locked; editing starts a new draft without carrying approvals.
  await page.getByRole("tab", { name: "Lịch sử" }).click();
  const newRev = page.getByRole("button", { name: "Tạo bản sửa mới" });
  if (await newRev.count()) await newRev.click();
  await expect(page.getByText("Bản nháp").first()).toBeVisible();

  // S04: "Duyệt tất cả" takes only clean machine-checked blocks and says how many it skips; the rest is approved block by block.
  await page.getByRole("tab", { name: "Soạn & nguồn" }).click();
  await page.getByRole("link", { name: "Tiếp: Duyệt" }).click(); // K4: each step ends with a button to the next one
  await expect(page.getByRole("button", { name: "Tiếp: Xuất bản" })).toBeDisabled(); // not everything is approved yet
  await expect(page.getByText(/Còn \d+ khối chưa duyệt\./).first()).toBeVisible();
  await page.getByRole("button", { name: "Duyệt tất cả khối không có cảnh báo" }).click();
  const confirm = page.getByRole("alertdialog", { name: "Xác nhận duyệt tất cả" });
  await expect(confirm).toContainText(/Duyệt \d+ khối, bỏ qua \d+ khối\./);
  await confirm.getByRole("button", { name: /^Duyệt \d+ khối$/ }).click();
  await expect(confirm).toHaveCount(0);
  const approve = page.getByRole("button", { name: "Duyệt khối này" });
  await expect(approve.first()).toBeVisible();
  // The queue re-renders after every decision, so a click can land on a card that is replaced a moment later and be lost
  // (no error on screen, the "x/y đã duyệt" counter does not move). Click again until the queue is empty.
  for (let i = 0; i < 200 && (await approve.count()) > 0; i++) {
    const before = await approve.count();
    await approve.first().click({ timeout: 5_000 }).catch(() => undefined); // the card may vanish between count and click
    await expect.poll(() => approve.count(), { timeout: 4_000 }).toBeLessThan(before).catch(() => undefined);
  }
  await expect(approve).toHaveCount(0);

  // S05: gate passes, explicit confirmation, publish, then assign to a class of the same grade.
  await page.getByRole("link", { name: "Tiếp: Xuất bản" }).click();
  await expect(page.getByRole("button", { name: "Tiếp: Giao bài" })).toBeDisabled(); // not published yet
  await expect(page.getByText("Hãy xuất bản bản này trước.")).toBeVisible();
  await expect(page.locator(".checklist li.fail")).toHaveCount(0);
  await page.getByText("Tôi đã đọc từng khối").click();
  await page.getByRole("button", { name: "Xuất bản", exact: true }).click();
  await expect(page.getByText(/đã xuất bản\./)).toBeVisible();
  await expect(page.getByRole("link", { name: "Tiếp: Giao bài" })).toBeVisible();
  // K5: a lesson day on or before the due day asks for confirmation before anything is saved
  await page.getByLabel("Ngày học (không bắt buộc)").fill("2030-05-10");
  await page.getByLabel("Hạn nộp", { exact: true }).fill("2030-05-10T23:59");
  await page.getByRole("button", { name: "Giao bài", exact: true }).click();
  const warn = page.getByRole("alertdialog", { name: "Xác nhận hạn nộp" });
  await expect(warn).toBeVisible();
  await expect(page.getByText(/Đã giao cho lớp/)).toHaveCount(0);
  await warn.getByRole("button", { name: "Sửa lại hạn" }).click();
  await page.getByLabel("Ngày học (không bắt buộc)").fill("2030-05-11"); // due moves to the day before: no warning
  await page.getByRole("button", { name: "Giao bài", exact: true }).click();
  await expect(page.getByText(/Đã giao cho lớp/)).toBeVisible();

  // S06: the published snapshot can be opened read-only from the history.
  await page.getByRole("tab", { name: "Lịch sử" }).click();
  await page.getByRole("button", { name: /^Xem bản #/ }).first().click();
  await expect(page.locator(".tree.snapshot .block-card").first()).toBeVisible();
});
