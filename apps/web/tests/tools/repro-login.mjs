// Repro tool: open /login on a deployed URL with a clean profile and watch what the page does.
// node tests/tools/repro-login.mjs <baseUrl> <outDir> [waitSeconds]
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium, webkit } from "@playwright/test";

const [base = "https://pre-class-ai.vercel.app", out = "test-results/login-repro", waitS = "90"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const rows = [];

for (const [name, type] of [["chromium", chromium], ["webkit", webkit]]) {
  for (const [vp, size] of [["390", { width: 390, height: 844 }], ["1280", { width: 1280, height: 800 }]]) {
    const browser = await type.launch();
    const ctx = await browser.newContext({ viewport: size, locale: "vi-VN" }); // fresh context = clean profile
    const page = await ctx.newPage();
    const reqs = new Map();
    const t0 = Date.now();
    const t = () => ((Date.now() - t0) / 1000).toFixed(1);
    const consoleMsgs = [];
    page.on("request", (r) => r.url().includes("/v1/") && reqs.set(r, { url: r.url().replace(/^https?:\/\/[^/]+/, ""), start: t(), status: "pending" }));
    page.on("response", (r) => { const e = reqs.get(r.request()); if (e) { e.status = r.status(); e.end = t(); } });
    page.on("requestfailed", (r) => { const e = reqs.get(r); if (e) { e.status = "FAILED " + (r.failure()?.errorText ?? ""); e.end = t(); } });
    page.on("console", (m) => ["error", "warning"].includes(m.type()) && consoleMsgs.push(`${t()}s ${m.type()}: ${m.text().slice(0, 160)}`));
    page.on("pageerror", (e) => consoleMsgs.push(`${t()}s pageerror: ${String(e).slice(0, 160)}`));
    await page.goto(`${base}/login`, { waitUntil: "domcontentloaded", timeout: 60_000 });
    const form = page.getByLabel("Email hoặc mã học sinh");
    const guestBtn = page.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" });
    const loading = page.getByText("Đang tải…");
    let formAt = null;
    const deadline = Date.now() + Number(waitS) * 1000;
    while (Date.now() < deadline) {
      if ((await form.isVisible().catch(() => false)) || (await guestBtn.isVisible().catch(() => false))) { formAt = t(); break; }
      await page.waitForTimeout(500);
    }
    const stillLoading = await loading.isVisible().catch(() => false);
    const shot = `${out}/${name}-${vp}.png`;
    await page.screenshot({ path: shot, fullPage: true });
    rows.push({ browser: name, vp, formVisibleAfterS: formAt, stillLoading, requests: [...reqs.values()], console: consoleMsgs, shot });
    console.log(`${name}/${vp}: form ${formAt ? "visible after " + formAt + "s" : "NOT visible in " + waitS + "s"}; loading=${stillLoading}`);
    for (const r of reqs.values()) console.log(`   ${r.url} -> ${r.status} (${r.start}s${r.end ? " .. " + r.end + "s" : ", never finished"})`);
    for (const c of consoleMsgs.slice(0, 4)) console.log("   console: " + c);
    await browser.close();
  }
}
writeFileSync(`${out}/result.json`, JSON.stringify(rows, null, 2));
