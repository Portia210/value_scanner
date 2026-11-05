import type { components } from "./schema";

type S = components["schemas"];
export type StocksOut = S["StocksOut"];
export type StockRow = S["StockRowOut"];
export type StockDetail = S["StockDetailOut"];
export type Criterion = S["CriterionOut"];
export type GuruScore = S["GuruScoreOut"];
export type CriteriaOut = S["CriteriaOut"];
export type RunOut = S["RunOut"];
export type LogLine = S["LogLine"];
export type SettingsOut = S["SettingsOut"];
export type EventOut = S["EventOut"];

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let csrf = "";
export const setCsrf = (token: string) => { csrf = token; };

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const res = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...rest,
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return (await res.json()) as T;
}
