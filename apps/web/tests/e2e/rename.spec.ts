import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// Writes the survey class's assignment names and puts them back: desktop only, dev/staging seed only.
test("teacher renames what students see, a guest sees the new name, and the old one comes back", async ({ page, browser, request }, info) => {
  test.skip(info.project.name !== "desktop-1280", "write flow runs once");
  const cfg = await request.get("/v1/auth/config");
  test.skip(!cfg.ok() || !(await cfg.json()).guestEnabled, "guest access is off on this stack");
  const NEW = "Bài 4. Tên mới để thử";

  await login(page, "gv.dia@preclass.local");
  await page.goto("/classes");
  const tab = page.getByRole("button", { name: /^KS \(khảo sát\)/ });
  await tab.click();
  await expect(tab).toHaveClass(/on/);
  await expect(page.getByRole("button", { name: "Đổi tên hiển thị" }).first()).toBeVisible();
  const cards = page.locator("li.card[id^='a-']").filter({ has: page.getByRole("button", { name: "Đổi tên hiển thị" }) });
  await expect(cards.first()).toBeVisible();
  const ids = await cards.evaluateAll((els) => els.map((e) => e.id)); // the list can reorder after a save: address cards by id
  const card = (id: string) => page.locator(`li.card[id="${id}"]`);
  const reset = async (id: string) => {
    await card(id).getByRole("button", { name: "Đổi tên hiển thị" }).click();
    const back = card(id).getByRole("button", { name: "Về tên của bản đã xuất bản" });
    if (await back.count()) await back.click();
    else await card(id).getByRole("button", { name: "Đổi tên hiển thị" }).click(); // nothing to reset: close the form
  };
  for (const id of ids) await reset(id); // start from the published names, whatever an earlier run left
  const old = (await card(ids[0]!).getByRole("heading").first().innerText()).trim();

  for (const id of ids) {
    const c = card(id);
    await c.getByRole("button", { name: "Đổi tên hiển thị" }).click();
    await c.getByLabel(/^Tên học sinh thấy/).fill("ab");
    await expect(c.getByText("Tên cần ít nhất 3 ký tự.")).toBeVisible();
    await expect(c.getByRole("button", { name: "Lưu tên" })).toBeDisabled();
    await c.getByLabel(/^Tên học sinh thấy/).fill(`  ${NEW}  `);
    await c.getByRole("button", { name: "Lưu tên" }).click();
    await expect(c.getByRole("heading").first()).toHaveText(NEW);
  }

  const guest = await (await browser.newContext()).newPage();
  await guest.goto("/thu?bai=dan-so-vung");
  await expect(guest.getByRole("heading", { name: NEW })).toBeVisible({ timeout: 30_000 });
  await guest.context().close();

  for (const id of ids) {
    await reset(id);
    await expect(card(id).getByRole("heading").first()).toHaveText(old);
  }
});
