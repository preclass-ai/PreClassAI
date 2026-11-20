// Visit every top-level screen as each role and report console errors (CSP violations show up there) and the CSP header.
// node tests/tools/csp-sweep.mjs <baseUrl> [password]
import { chromium } from "@playwright/test";

const base = process.argv[2] ?? "http://localhost:3100";
const dflt = process.argv[3] ?? process.env.SEED_PASSWORD ?? "preclass-demo";
const passwordFor = (who) =>
  who.startsWith("admin@") ? process.env.SEED_ADMIN_PASSWORD ?? dflt : who.startsWith("HS") ? process.env.SEED_STUDENT_PASSWORD ?? dflt : process.env.SEED_TEACHER_PASSWORD ?? dflt;
const plan = [
  ["gv.dia@preclass.local", ["/lessons", "/lessons/new", "/sources", "/classes"]],
  ["admin@preclass.local", ["/admin/audit"]],
  ["HS10-20", ["/student"]],
];
const browser = await chromium.launch();
let bad = 0;
for (const [who, paths] of plan) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on("console", (m) => m.type() === "error" && !m.text().includes("401") && errs.push(m.text().slice(0, 200)));
  page.on("pageerror", (e) => errs.push("pageerror " + String(e).slice(0, 200)));
  await page.goto(`${base}/login`);
  const toggle = page.getByText("Giáo viên / có tài khoản");
  await page.getByLabel("Email hoặc mã học sinh").or(toggle).first().waitFor();
  if (await toggle.isVisible()) await toggle.click();
  await page.getByLabel("Email hoặc mã học sinh").fill(who);
  await page.getByLabel("Mật khẩu").fill(passwordFor(who));
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30_000 });
  for (const p of paths) {
    const r = await page.goto(base + p, { waitUntil: "networkidle" });
    const csp = r?.headers()["content-security-policy"] ?? "(none)";
    console.log(`${who} ${p}: ${r?.status()} csp=${csp.startsWith("default-src 'self'") ? "yes" : "NO"}`);
  }
  console.log(`  ${who}: console errors = ${errs.length}`, errs.slice(0, 3));
  bad += errs.length;
  await ctx.close();
}
await browser.close();
process.exit(bad ? 1 : 0);
