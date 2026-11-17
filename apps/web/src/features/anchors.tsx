import type { Schemas } from "@/lib/api";
import { fmtNumber } from "@/lib/format";

const ANCHOR_KIND: Record<Schemas["AnchorOut"]["kind"], string> = {
  PARAGRAPH: "Đoạn",
  HEADING: "Tiêu đề",
  TABLE_CELL: "Ô bảng",
  TABLE_ROW: "Hàng bảng",
};

export function anchorKind(kind: Schemas["AnchorOut"]["kind"]): string {
  return ANCHOR_KIND[kind];
}

/** Locator such as {table:0,row:2,col:1} → "Bảng 1, hàng 3, cột 2" (1-based for teachers). */
export function locatorText(locator: Record<string, unknown>): string {
  const parts: string[] = [];
  const n = (k: string) => (typeof locator[k] === "number" ? (locator[k] as number) + 1 : null);
  if (n("paragraph") !== null) parts.push(`đoạn ${n("paragraph")}`);
  if (n("table") !== null) parts.push(`bảng ${n("table")}`);
  if (n("row") !== null) parts.push(`hàng ${n("row")}`);
  if (n("col") !== null) parts.push(`cột ${n("col")}`);
  return parts.join(", ");
}

export function AnchorTable({ anchors }: { anchors: Schemas["AnchorOut"][] }) {
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
              <td>{a.numbers?.length ? a.numbers.map((x) => fmtNumber(x)).join("; ") : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
