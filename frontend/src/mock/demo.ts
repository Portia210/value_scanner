// DEMO DATA ONLY — illustrative numbers for the design example, not real analysis results.
import type { CompanyType, CriterionResult, GuruKey, RunInfo, Settings, StockDetail, StockRow } from "../types";

type Raw = [string, string, string, string, CompanyType, number, number, number,
  [number, number], [number, number], [number, number], [number, number]];

const raw: Raw[] = [
  ["CSW", "CSW Industrials", "Industrials", "Specialty Industrial Machinery", "regular", 5.1, 0.86, 0.34, [8, 8], [6, 7], [5, 6], [7, 8]],
  ["DCI", "Donaldson", "Industrials", "Specialty Industrial Machinery", "regular", 7.8, 0.81, 0.27, [8, 8], [6, 7], [4, 6], [6, 8]],
  ["UTHR", "United Therapeutics", "Healthcare", "Drug Manufacturers", "pharma", 15.2, 0.78, 0.31, [8, 8], [5, 6], [5, 6], [5, 8]],
  ["GNTX", "Gentex", "Consumer Discretionary", "Auto Parts", "cyclical", 6.4, 0.74, 0.22, [7, 8], [5, 7], [4, 6], [6, 8]],
  ["SNA", "Snap-on", "Industrials", "Tools & Accessories", "regular", 17.5, 0.69, 0.12, [8, 8], [5, 7], [3, 6], [6, 8]],
  ["MPWR", "Monolithic Power", "Technology", "Semiconductors", "tech", 30.1, 0.83, -0.21, [8, 8], [4, 6], [4, 6], [7, 8]],
  ["NVDA", "NVIDIA", "Technology", "Semiconductors", "tech", 180, 0.88, -0.46, [8, 8], [3, 6], [4, 6], [7, 8]],
  ["CPRT", "Copart", "Industrials", "Specialty Business Services", "regular", 45, 0.76, -0.18, [8, 8], [4, 7], [3, 6], [6, 8]],
  ["FAST", "Fastenal", "Industrials", "Industrial Distribution", "regular", 47, 0.72, -0.33, [8, 8], [4, 7], [3, 6], [5, 8]],
  ["DHI", "D.R. Horton", "Consumer Discretionary", "Residential Construction", "cyclical", 48, 0.58, 0.29, [7, 8], [5, 7], [3, 6], [3, 8]],
  ["PHM", "PulteGroup", "Consumer Discretionary", "Residential Construction", "cyclical", 24, 0.61, 0.33, [7, 8], [5, 7], [3, 6], [4, 8]],
  ["TROW", "T. Rowe Price", "Financials", "Asset Management", "financial", 22, 0.55, 0.18, [6, 8], [4, 5], [2, 4], [4, 8]],
  ["LULU", "Lululemon", "Consumer Discretionary", "Apparel Retail", "cyclical", 20, 0.67, 0.08, [8, 8], [4, 7], [3, 6], [5, 8]],
  ["AMAT", "Applied Materials", "Technology", "Semiconductor Equipment", "tech", 140, 0.71, -0.05, [8, 8], [4, 6], [3, 6], [5, 8]],
  ["COLM", "Columbia Sportswear", "Consumer Discretionary", "Apparel Manufacturing", "cyclical", 4.6, 0.42, 0.15, [6, 8], [3, 7], [2, 6], [3, 8]],
  ["OLLI", "Ollie's Bargain", "Consumer Staples", "Discount Stores", "regular", 6.8, 0.49, -0.12, [7, 8], [3, 7], [3, 6], [4, 8]],
  ["VEEV", "Veeva Systems", "Healthcare", "Health Information Services", "tech", 38, 0.64, -0.38, [8, 8], [3, 6], [3, 6], [6, 8]],
  ["MNST", "Monster Beverage", "Consumer Staples", "Beverages", "regular", 55, 0.66, -0.28, [8, 8], [3, 7], [4, 6], [5, 8]],
  ["AFG", "American Financial", "Financials", "Insurance", "financial", 10.5, 0.47, 0.05, [6, 8], [3, 5], [2, 4], [3, 8]],
  ["KEYS", "Keysight", "Technology", "Scientific Instruments", "tech", 27, 0.52, -0.09, [7, 8], [3, 6], [3, 6], [4, 8]],
];

const guru = ([passed, total]: [number, number]) => ({ passed, total, score: passed / total });

export const demoStocks: StockRow[] = raw.map((r) => ({
  symbol: r[0], name: r[1], sector: r[2], industry: r[3], ctype: r[4], marketCapB: r[5],
  quality: r[6], opportunity: r[7],
  gurus: { screen: guru(r[8]), graham: guru(r[9]), fisher: guru(r[10]), piotroski: guru(r[11]) },
}));

const c = (guru: GuruKey, id: string, title: string, display: string, status: CriterionResult["status"],
  strength: number, extra: Partial<CriterionResult> = {}): CriterionResult =>
  ({ guru, id, title, display, status, strength, ...extra });

export function demoDetail(symbol: string): StockDetail | undefined {
  const row = demoStocks.find((s) => s.symbol === symbol);
  if (!row) return undefined;
  return {
    ...row,
    dataAsOf: "03.11.2026",
    criteria: [
      c("screen", "S1", "שווי שוק > 2B$", "$5.1B", "PASS", 1, { op: ">", value: 5.1, threshold: 2, scaleMax: 8 }),
      c("screen", "S2", "מכפיל רווח (P/E) > 5", "13.1", "PASS", 1, { op: ">", value: 13.1, threshold: 5, scaleMax: 30 }),
      c("screen", "S3", "צמיחת הכנסות 5Y > 0%", "+11.9%", "PASS", 1, { op: ">", value: 11.9, threshold: 0, scaleMax: 30 }),
      c("screen", "S4", "שולי רווח נקי > 8%", "17.0%", "PASS", 1, { op: ">", value: 17, threshold: 8, scaleMax: 30 }),
      c("screen", "S5", "צמיחת EPS 5Y > 0%", "+17.1%", "PASS", 1, { op: ">", value: 17.1, threshold: 0, scaleMax: 30 }),
      c("screen", "S6", "חוב להון (D/E) < 0.5", "0.24", "PASS", 1, { op: "<", value: 0.24, threshold: 0.5, scaleMax: 1 }),
      c("screen", "S7", "יחס שוטף > 2", "2.26", "PASS", 0.75, { op: ">", value: 2.26, threshold: 2, scaleMax: 4, note: "עובר, אבל פחות מ-20% מעל הסף" }),
      c("screen", "S8", "תשואה להון 5Y > 10%", "16.8%", "PASS", 1, { op: ">", value: 16.8, threshold: 10, scaleMax: 30 }),
      c("graham", "G1", "הכנסות > 350M$", "$1,190M", "PASS", 1, { op: ">", value: 1190, threshold: 350, scaleMax: 1500 }),
      c("graham", "G2", "יחס שוטף > 2", "2.26", "PASS", 0.75, { op: ">", value: 2.26, threshold: 2, scaleMax: 4 }),
      c("graham", "G3", "הון חוזר > חוב לזמן ארוך", "$410M / $236M", "PASS", 1, { op: ">", value: 410, threshold: 236, scaleMax: 600 }),
      c("graham", "G4", "מכפיל רווח (P/E) < 15", "13.1", "PASS", 0.75, { op: "<", value: 13.1, threshold: 15, scaleMax: 30 }),
      c("graham", "G5", "מכפיל גראהם P/E × P/B < 22", "19.6", "PASS", 0.75, { op: "<", value: 19.6, threshold: 22, scaleMax: 40 }),
      c("graham", "G6", "צמיחת EPS (2 ראשונות → 2 אחרונות) > 30%", "41%", "PASS", 1, { op: ">", value: 41, threshold: 30, scaleMax: 80 }),
      c("graham", "G7", "אף שנה הפסדית ב-5 שנים", "שנה הפסדית אחת", "FAIL", 0, { note: "דמה: הפסד ב-2021 לצורך הדגמה" }),
      c("fisher", "F1", "מכפיל מכירות (P/S) < 1.5", "2.1", "FAIL", 0.25, { op: "<", value: 2.1, threshold: 1.5, scaleMax: 4 }),
      c("fisher", "F2", "צמיחת EPS שנתית ממוצעת > 15%", "17.4%", "PASS", 0.75, { op: ">", value: 17.4, threshold: 15, scaleMax: 40 }),
      c("fisher", "F3", "שולי רווח נקי ממוצע 5Y > 5%", "15.3%", "PASS", 1, { op: ">", value: 15.3, threshold: 5, scaleMax: 25 }),
      c("fisher", "F4", "חוב להון (D/E) < 0.4", "0.24", "PASS", 1, { op: "<", value: 0.24, threshold: 0.4, scaleMax: 1 }),
      c("fisher", "F5", "תזרים חופשי למניה > 0", "$9.80", "PASS", 1, { op: ">", value: 9.8, threshold: 0, scaleMax: 15 }),
      c("fisher", "F6", "שווי שוק / מו\"פ בין 5 ל-15", "לא רלוונטי", "NA", 0, { note: "חל רק על טכנולוגיה ופארמה" }),
      c("piotroski", "P1", "P/B נמוך ב-20% מחציון הסקטור", "לא רלוונטי", "NA", 0, { note: "חל רק על חברות פיננסיות" }),
      c("piotroski", "P2", "יחס מהיר עלה משנה שעברה", "1.66 ← 1.68", "FAIL", 0, { op: "rise" }),
      c("piotroski", "P3", "חוב לז\"א / נכסים ירד", "0.14 ← 0.17", "PASS", 1, { op: "fall" }),
      c("piotroski", "P4", "תזרים שוטף > 0 וגדול מהרווח הנקי", "$212M > $167M", "PASS", 1),
      c("piotroski", "P5", "ROA חיובי ועלה", "12.4% ← 11.9%", "PASS", 1, { op: "rise" }),
      c("piotroski", "P6", "כמות מניות ירדה", "16.8M ← 16.8M", "FAIL", 0, { op: "fall", note: "ללא שינוי נחשב כישלון" }),
      c("piotroski", "P7", "שולי רווח גולמי עלו", "45.2% ← 43.9%", "PASS", 1, { op: "rise" }),
      c("piotroski", "P8", "מחזור נכסים עלה", "0.74 ← 0.71", "PASS", 1, { op: "rise" }),
    ],
    mos: [
      { id: "O1", title: "מספר גראהם", formula: "1 − √(P/E × P/B ÷ 22)", mos: 0.06, applies: true },
      { id: "O2", title: "מכפיל הוגן", formula: "1 − P/E ÷ 15", mos: 0.13, applies: true },
      { id: "O3", title: "מול ההיסטוריה", formula: "1 − P/E ÷ חציון P/E ב-5 שנים", mos: 0.34, applies: true },
      { id: "O4", title: "מכפיל מכירות", formula: "1 − P/S ÷ 1.5", mos: -0.4, applies: true },
    ],
    series: {
      years: ["2021", "2022", "2023", "2024", "2025"],
      eps: [5.1, 6.4, 8.2, 8.9, 9.6],
      netMargin: [13.2, 14.1, 15.8, 16.4, 17.0],
      roe: [14.9, 15.8, 17.6, 18.1, 17.4],
    },
  };
}

export const demoSettings: Settings = { intervalDays: 3, qualityMin: 0.7, mosMin: 0.2 };

export const demoRuns: RunInfo[] = [
  { id: 43, trigger: "manual", status: "running", startedAt: "05.11.2026 19:02", durationMin: null, ok: 61, failed: 0, kind: "full" },
  { id: 42, trigger: "schedule", status: "succeeded", startedAt: "03.11.2026 03:00", durationMin: 38, ok: 108, failed: 2, kind: "full" },
  { id: 41, trigger: "schedule", status: "succeeded", startedAt: "02.11.2026 03:00", durationMin: 1, ok: 110, failed: 0, kind: "prices" },
  { id: 40, trigger: "schedule", status: "interrupted", startedAt: "31.10.2026 03:00", durationMin: 12, ok: 40, failed: 0, kind: "full" },
  { id: 39, trigger: "manual", status: "failed", startedAt: "30.10.2026 22:14", durationMin: 3, ok: 0, failed: 0, kind: "full" },
];
