// dd/mm/yyyy with a 4-digit year ("20/11/2027"): the short style prints a 2-digit year that students misread.
const dateTime = new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
const dateOnly = new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });

export function fmtDate(iso: string | null | undefined): string {
  return iso ? dateOnly.format(new Date(iso)) : "Chưa có";
}
const number = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });

export function fmtDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "Chưa có";
}

export function fmtNumber(n: number | null | undefined): string {
  return n === null || n === undefined ? "Chưa có" : number.format(n);
}

/**
 * A student's numeric answer → number, or the reason it cannot be read. Accepts "17,3", "17.3", "-2,5", "1 234" and the
 * Vietnamese grouped form "1.234,5" / "1.234.567". A lone "1.234" stays 1.234 (decimal), as before. Units, hex
 * ("0x11"), exponents and "Infinity" are refused instead of being silently converted by Number().
 */
export function parseAnswerNumber(raw: string): { value: number } | { error: string } {
  const s = raw.trim().replace(/(\d)[\s ]+(?=\d)/g, "$1");
  if (/^[+-]?\d+([.,]\d+)?$/.test(s)) return { value: Number(s.replace(",", ".")) };
  if (/^[+-]?\d{1,3}(\.\d{3})+(,\d+)?$/.test(s)) return { value: Number(s.replace(/\./g, "").replace(",", ".")) };
  if (/\p{L}/u.test(s)) return { error: "Chỉ nhập số, không ghi đơn vị (ví dụ: 17,3)." };
  return { error: "Đáp số chưa đúng dạng số (ví dụ: 17,3 hoặc -2,5)." };
}

export function fmtPercent(rate: number | null | undefined): string {
  return rate === null || rate === undefined ? "Chưa có" : `${Math.round(rate * 100)}%`;
}

/** `<input type="datetime-local">` value (local time) → ISO-8601 with offset, as the API expects. */
export function localInputToIso(value: string): string {
  return new Date(value).toISOString();
}

/** Date → `<input type="datetime-local">` value in local time. */
export function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "Trước buổi học 1 ngày": the lesson day (`yyyy-mm-dd` from a date input) minus one day at 23:59, as a datetime-local value. */
/** True when the lesson day (YYYY-MM-DD) is not after the due day of a datetime-local value: students could still hand in after the lesson. */
export function dueNotBeforeLesson(lessonDay: string, dueAt: string): boolean {
  return !!lessonDay && !!dueAt && dueAt.slice(0, 10) >= lessonDay;
}

export function dueDayBefore(lessonDay: string): string {
  const d = new Date(`${lessonDay}T00:00:00`);
  d.setDate(d.getDate() - 1);
  return toLocalInput(new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59));
}
