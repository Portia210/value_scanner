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
