import type { Schemas } from "@/lib/api";
import { fmtNumber } from "@/lib/format";

type Anchor = Schemas["AnchorOut"];

const ANCHOR_KIND: Record<Anchor["kind"], string> = {
  PARAGRAPH: "Đoạn",
  HEADING: "Tiêu đề",
  TABLE_CELL: "Ô bảng",
  TABLE_ROW: "Hàng bảng",
};

export function anchorKind(kind: Anchor["kind"]): string {
  return ANCHOR_KIND[kind];
}

/** 0-based column index → spreadsheet letters (0 → A, 26 → AA). */
export function colName(i: number): string {
  let s = "";
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

/**
 * Where an anchor sits in its file, for teachers (1-based): "Trang 3, đoạn 2", "Sheet Dân số, ô C5", "Slide 4, đoạn 1",
 * "Bảng 1, hàng 3, cột 2" (DOCX). Locators come from the server: PDF {page, para} (both 1-based), XLSX {sheet, row, col}
 * (0-based), PPTX {slide, shape, para | row, col} (slide 1-based, rest 0-based), DOCX {para_index | table,row,col}.
 */
export function locatorText(l: Record<string, unknown>): string {
  const num = (k: string) => (typeof l[k] === "number" ? (l[k] as number) : null);
  const row = num("row");
  const col = num("col");
  if (typeof l.sheet === "string" && row !== null && col !== null) return `Sheet ${l.sheet}, ô ${colName(col)}${row + 1}`;
  const slide = num("slide");
  if (slide !== null) {
    if (row !== null && col !== null) return `Slide ${slide}, bảng hàng ${row + 1}, cột ${col + 1}`;
    return `Slide ${slide}${num("para") !== null ? `, đoạn ${num("para")! + 1}` : ""}`;
  }
  const page = num("page");
  if (page !== null) return `Trang ${page}${num("para") !== null ? `, đoạn ${num("para")}` : ""}`;
  const parts: string[] = [];
  const one = (k: string) => (num(k) !== null ? num(k)! + 1 : null);
  if (one("para_index") !== null) parts.push(`đoạn ${one("para_index")}`);
  if (one("paragraph") !== null) parts.push(`đoạn ${one("paragraph")}`);
  if (one("table") !== null) parts.push(`bảng ${one("table")}`);
  if (row !== null) parts.push(`hàng ${row + 1}`);
  if (col !== null) parts.push(`cột ${col + 1}`);
  return parts.join(", ");
}

/** The page / sheet / slide an anchor belongs to ("" for formats without such a unit). */
export function groupOf(l: Record<string, unknown>): string {
  if (typeof l.sheet === "string") return `Sheet ${l.sheet}`;
  if (typeof l.slide === "number") return `Slide ${l.slide}`;
  if (typeof l.page === "number") return `Trang ${l.page}`;
  return "";
}

export function AnchorTable({ anchors }: { anchors: Anchor[] }) {
  if (anchors.length === 0) return <p className="empty">Không có đoạn nguồn.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Mã</th>
            <th>Loại</th>
            <th>Nội dung</th>
            <th>Số liệu nhận ra</th>
          </tr>
        </thead>
        <tbody>
          {anchors.map((a) => (
            <tr key={a.id}>
              <td className="mono">{a.code}</td>
              <td>
                {ANCHOR_KIND[a.kind]}
                <div className="muted small">{locatorText(a.locator)}</div>
              </td>
              <td className="excerpt">{a.excerpt}</td>
              <td>{a.numbers?.length ? a.numbers.map((x) => fmtNumber(x)).join("; ") : "Không có"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const PREVIEW_MAX = 200;

/** Read-only preview right after an upload: anchors grouped by page / sheet / slide, each group collapsible. */
export function AnchorPreview({ anchors }: { anchors: Anchor[] }) {
  const shown = anchors.slice(0, PREVIEW_MAX);
  const groups = new Map<string, Anchor[]>();
  for (const a of shown) groups.set(groupOf(a.locator) || "Nội dung", [...(groups.get(groupOf(a.locator) || "Nội dung") ?? []), a]);
  return (
    <div className="anchor-preview">
      {[...groups].map(([name, items], i) => (
        <details key={name} open={i === 0}>
          <summary>
            {name} <span className="muted small">· {items.length} đoạn</span>
          </summary>
          <ul>
            {items.map((a) => (
              <li key={a.id}>
                <span className="muted small">{locatorText(a.locator)}</span> {a.excerpt}
              </li>
            ))}
          </ul>
        </details>
      ))}
      {anchors.length > PREVIEW_MAX ? <p className="muted small">… và {anchors.length - PREVIEW_MAX} đoạn khác (xem đủ ở trang nguồn).</p> : null}
    </div>
  );
}
