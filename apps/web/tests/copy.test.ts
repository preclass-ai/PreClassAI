import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// Humanized copy: no long dashes in what students and teachers read.
const ROOTS = ["app", "src"].map((d) => path.join(import.meta.dirname, "..", d));

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const f = path.join(dir, n);
    return statSync(f).isDirectory() ? files(f) : /\.(ts|tsx)$/.test(n) ? [f] : [];
  });
}

const strip = (line: string) => line.replace(/\/\*.*?\*\//g, "").replace(/(^|\s)\/\/.*$/, "$1"); // comments are not UI

describe("UI copy", () => {
  it("has no em dash or spaced en dash in any UI string", () => {
    const bad: string[] = [];
    for (const f of ROOTS.flatMap(files)) {
      readFileSync(f, "utf8").split("\n").forEach((line, i) => {
        if (/^\s*(\*|\/\/|\/\*)/.test(line)) return;
        if (/—| – /.test(strip(line))) bad.push(`${path.relative(path.join(import.meta.dirname, ".."), f)}:${i + 1}`);
      });
    }
    expect(bad).toEqual([]);
  });
});
