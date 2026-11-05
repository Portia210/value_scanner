import type { CompanyType, GuruKey } from "./types";

export const pct = (v: number | null, signed = true): string =>
  v === null ? "—" : `${signed && v > 0 ? "+" : ""}${Math.round(v * 100)}%`;

export const score100 = (v: number | null): string => (v === null ? "—" : String(Math.round(v * 100)));

export const GURU_LABELS: Record<GuruKey, string> = {
  screen: "סינון ראשוני",
  graham: "גראהם",
  fisher: "פישר",
  piotroski: "פיוטרוסקי",
};

export const GURU_ORDER: GuruKey[] = ["screen", "graham", "fisher", "piotroski"];

export const TYPE_LABELS: Record<CompanyType, string> = {
  tech: "טכנולוגיה",
  pharma: "פארמה",
  financial: "פיננסית",
  cyclical: "מחזורית",
  regular: "רגילה",
};

/** Text direction for a value/formula: right-to-left if it contains Hebrew, else left-to-right. */
export const dirOf = (text: string): "rtl" | "ltr" => (/[֐-׿]/.test(text) ? "rtl" : "ltr");
