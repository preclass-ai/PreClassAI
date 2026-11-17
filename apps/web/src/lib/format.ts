const dateTime = new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" });
const number = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });

export function fmtDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "—";
}

export function fmtNumber(n: number | null | undefined): string {
  return n === null || n === undefined ? "—" : number.format(n);
}

export function fmtPercent(rate: number | null | undefined): string {
  return rate === null || rate === undefined ? "—" : `${Math.round(rate * 100)}%`;
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
