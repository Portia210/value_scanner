export const pct = (v: number | null | undefined, signed = true): string =>
  v === null || v === undefined ? "—" : `${signed && v > 0 ? "+" : ""}${Math.round(v * 100)}%`;

export const score100 = (v: number | null | undefined): string => (v === null || v === undefined ? "—" : String(Math.round(v * 100)));

export const GURU_LABELS: Record<string, string> = {
  screen: "סינון ראשוני",
  graham: "גראהם",
  fisher: "פישר",
  piotroski: "פיוטרוסקי",
};

export const GURU_ORDER = ["screen", "graham", "fisher", "piotroski"] as const;

export const TYPE_LABELS: Record<string, string> = {
  tech: "טכנולוגיה",
  pharma: "פארמה",
  financial: "פיננסית",
  cyclical: "מחזורית",
  regular: "רגילה",
};

export const REASON_LABELS: Record<string, string> = {
  price: "שינוי מחיר",
  report: "דוחות חדשים",
  new_symbol: "מניה חדשה",
  delisted: "ירדה מהמסחר",
  data: "שינוי בנתונים",
};

export const FILTER_LABELS: Record<string, string> = {
  marketCap: "שווי שוק",
  peRatio: "P/E",
  revenueGrowth5Y: "צמיחת הכנסות 5 שנים",
  profitMargin: "שולי רווח",
  epsGrowth5Y: "צמיחת EPS 5 שנים",
  debtEquity: "חוב להון",
  currentRatio: "Current ratio",
  roe5y: "ROE 5 שנים",
};

/** Text direction for a value/formula: right-to-left if it contains Hebrew, else left-to-right. */
export const dirOf = (text: string): "rtl" | "ltr" => (/[֐-׿]/.test(text) ? "rtl" : "ltr");

/** "2026-11-05T21:37:26Z" -> "05.11.2026 21:37" (local time). */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function date(iso: string | null | undefined): string {
  return dateTime(iso).slice(0, 10) || "—";
}

/** Compact number: 4,483,828,889 -> "4.5B"; 12.345 -> "12.35". */
export function num(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e4) return Math.round(v).toLocaleString("en-US");
  return String(Number(v.toFixed(digits)));
}

export const marketCapB = (v: number | null | undefined): number => (v ? v / 1e9 : 0);
export const primaryType = (labels: string[]): string => labels[0] ?? "regular";

/** "2026-11-05" (a calendar date, no time) as a local Date at midnight. */
function calendarDate(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Whole days from today to the given calendar date (negative = in the past). */
export function daysFromToday(day: string | null | undefined, today = new Date()): number | null {
  if (!day) return null;
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((calendarDate(day).getTime() - t.getTime()) / 86_400_000);
}

export const fullDate = (day: string) => {
  const d = calendarDate(day);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}`;
};

/** A calendar date as "היום" / "אתמול" / "מחר", otherwise dd.mm.yyyy. */
export function relativeDay(day: string | null | undefined, today = new Date()): string {
  if (!day) return "—";
  const n = daysFromToday(day, today);
  if (n === 0) return "היום";
  if (n === -1) return "אתמול";
  if (n === 1) return "מחר";
  return fullDate(day);
}

export const EARNINGS_SOON_DAYS = 15;

/** "נכון ל…": להיום / לאתמול / ל-05.11.2026. */
export function asOf(day: string | null | undefined, today = new Date()): string {
  const r = relativeDay(day, today);
  return r === "היום" || r === "אתמול" ? `ל${r}` : `ל-${r}`;
}

/** "עדכני להיום (16:40)" / "עדכני לאתמול (16:40)" / "עדכני ל-05.11.2026" for a timestamp. */
export function updated(iso: string | null | undefined, today = new Date()): string {
  if (!iso) return "—";
  const day = localDay(iso);
  const r = relativeDay(day, today);
  if (r !== "היום" && r !== "אתמול") return `עדכני ל-${r}`;
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `עדכני ל${r} (${p(d.getHours())}:${p(d.getMinutes())})`;
}

/** The local calendar day ("2026-11-06") of an ISO timestamp such as "2026-11-06T15:09:00Z". */
export function localDay(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
