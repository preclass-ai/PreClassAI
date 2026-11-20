// node tests/tools/shot-student-home.mjs <baseUrl> <outDir>: enter as a guest and screenshot the lesson list at 390 and 1280.
import { mkdirSync } from "node:fs";
import { chromium } from "@playwright/test";
const [base = "http://localhost:3100", out = "test-results/due-date"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const [vp, size] of [["390", { width: 390, height: 844 }], ["1280", { width: 1280, height: 800 }]]) {
  const ctx = await browser.newContext({ viewport: size, locale: "vi-VN" });
  const page = await ctx.newPage();
  await page.goto(`${base}/login`);
  await page.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" }).click();
  await page.getByRole("heading", { name: "Bài được giao" }).waitFor();
  const cols = await page.evaluate(() => getComputedStyle(document.querySelector(".assignment-grid")).gridTemplateColumns.split(" ").length);
  const due = await page.getByText(/Hạn nộp/).count();
  console.log(`${vp}px: grid columns=${cols}, "Hạn nộp" shown=${due}`);
  await page.screenshot({ path: `${out}/student-home-${vp}.png`, fullPage: true });
  await ctx.close();
}
await browser.close();
