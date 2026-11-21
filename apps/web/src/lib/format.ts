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
export function dueDayBefore(lessonDay: string): string {
  const d = new Date(`${lessonDay}T00:00:00`);
  d.setDate(d.getDate() - 1);
  return toLocalInput(new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59));
}
