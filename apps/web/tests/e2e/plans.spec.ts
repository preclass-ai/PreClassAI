import path from "node:path";
import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// Teacher: upload an invented lesson plan, check what was read, confirm one answer, build the pre-class draft.
const shot = (name: string, project: string) => `test-results/plans/${name}-${project}.png`;

test("teacher reads a lesson plan and builds the pre-class draft", async ({ page }, info) => {
  const n = info.project.name;
  await login(page, "gv.dia@preclass.local");
  await page.goto("/plans");
  await page.setInputFiles("#plan-file", path.join(import.meta.dirname, "fixtures", "plan-mau.docx"));
  await page.getByRole("button", { name: "Đọc giáo án" }).click();
  await expect(page.getByRole("heading", { name: "CHỦ ĐỀ MẪU" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("Gợi ý hạn nộp: 21/09/2026")).toBeVisible();
  const mcq = page.locator('section[aria-labelledby="mcq"]'); // AI drafts (when QUIZ_GEN is on) have their own "Cần xác nhận" badges
  await expect(mcq.getByText("Cần xác nhận")).toHaveCount(1);
  await page.screenshot({ path: shot("plan-check", n), fullPage: n !== "webkit-390" });

  await page.locator("fieldset").nth(1).getByLabel("D. Bốn").click();
  await expect(mcq.getByText("Cần xác nhận")).toHaveCount(0);
  await page.getByRole("button", { name: "Tạo bài chuẩn bị trước giờ học" }).click();
  await expect(page).toHaveURL(/\/lessons\/.+tab=editor/, { timeout: 60_000 });
  await page.screenshot({ path: shot("plan-lesson", n), fullPage: n !== "webkit-390" });
});
