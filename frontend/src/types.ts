// Shapes the API will return. Until the backend exists these are filled from src/mock/demo.ts;
// later they are replaced by types generated from FastAPI's OpenAPI schema.

export type GuruKey = "screen" | "graham" | "fisher" | "piotroski";
export type Status = "PASS" | "FAIL" | "NA";
export type CompanyType = "tech" | "pharma" | "financial" | "cyclical" | "regular";

export interface GuruScore {
  score: number | null; // 0..1, null when coverage is too low
  passed: number;
  total: number; // criteria that could be computed (not NA)
}

export interface StockRow {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  ctype: CompanyType;
  marketCapB: number;
  gurus: Record<GuruKey, GuruScore>;
  quality: number | null;
  opportunity: number | null; // margin of safety, e.g. 0.25 = 25% below fair value
}

export interface CriterionResult {
  id: string;
  guru: GuruKey;
  title: string;
  status: Status;
  strength: number; // 0, 0.25, 0.75, 1
  display: string; // formatted value
  op?: ">" | "<" | "between" | "rise" | "fall";
  value?: number;
  threshold?: number;
  scaleMax?: number; // for drawing the gauge
  note?: string;
}

export interface MosComponent {
  id: string;
  title: string;
  formula: string;
  mos: number | null;
  applies: boolean;
}

export interface StockDetail extends StockRow {
  criteria: CriterionResult[];
  mos: MosComponent[];
  series: { years: string[]; eps: number[]; netMargin: number[]; roe: number[] };
  dataAsOf: string;
}

export interface RunInfo {
  id: number;
  trigger: "schedule" | "manual";
  status: "running" | "succeeded" | "failed" | "interrupted";
  startedAt: string;
  durationMin: number | null;
  ok: number;
  failed: number;
  kind: "full" | "prices";
}

export interface Settings {
  intervalDays: number;
  qualityMin: number;
  mosMin: number;
}
