/** Objectives of a lesson plan come as flat lines. A line such as "a) Năng lực chung:" or "2. Phẩm chất" names a group of the lines after it:
 * show it as a heading, not as a bullet. Text after the colon ("Năng lực chung: tự chủ…") stays as the first bullet of the group. */
export type ObjectiveLine = { text: string };
export type ObjectiveGroup<T extends ObjectiveLine> = { title: string | null; items: T[] };

const HEAD = /^(?:[a-dA-D]|\d+)?\s*[.)]?\s*((?:về\s+)?(?:năng lực|phẩm chất|kiến thức)[^:]{0,40}?)\s*(?::\s*(.*))?$/iu;

export function splitObjectives<T extends ObjectiveLine>(lines: T[]): ObjectiveGroup<T>[] {
  const groups: ObjectiveGroup<T>[] = [];
  let cur: ObjectiveGroup<T> | null = null;
  for (const line of lines) {
    const text = line.text.normalize("NFC").trim();
    const m = HEAD.exec(text);
    const isHead = m !== null && (text.includes(":") || /^(?:[a-dA-D]|\d+)\s*[.)]/u.test(text) || text.split(/\s+/).length <= 4);
    if (m && isHead) {
      cur = { title: (m[1] ?? "").trim(), items: [] };
      groups.push(cur);
      const rest = (m[2] ?? "").trim();
      if (rest) cur.items.push({ ...line, text: rest });
      continue;
    }
    if (!cur) {
      cur = { title: null, items: [] };
      groups.push(cur);
    }
    cur.items.push(line);
  }
  return groups;
}
