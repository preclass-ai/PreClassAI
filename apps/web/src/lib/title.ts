/** Lesson / assignment name rules, same as the API: spaces trimmed and collapsed, 3 to 120 characters. Returns an error text or null. */
export const TITLE_MIN = 3;
export const TITLE_MAX = 120;

export const cleanTitle = (raw: string) => raw.trim().replace(/\s+/g, " ");

export function checkTitle(raw: string): string | null {
  const t = cleanTitle(raw);
  if (!t) return "Tên không được để trống.";
  if (t.length < TITLE_MIN) return `Tên cần ít nhất ${TITLE_MIN} ký tự.`;
  if (t.length > TITLE_MAX) return `Tên không quá ${TITLE_MAX} ký tự (đang ${t.length}).`;
  return null;
}
