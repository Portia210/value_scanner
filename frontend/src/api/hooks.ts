import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CriteriaOut, type EventOut, type LogLine, type RunOut, type SettingsOut, type StockDetail, type StocksOut } from "./client";

export const useStocks = () => useQuery({ queryKey: ["stocks"], queryFn: () => api<StocksOut>("/stocks") });
export const useStock = (symbol: string) =>
  useQuery({ queryKey: ["stock", symbol], queryFn: () => api<StockDetail>(`/stocks/${encodeURIComponent(symbol)}`), retry: false });
export const useCriteria = () => useQuery({ queryKey: ["criteria"], queryFn: () => api<CriteriaOut>("/criteria"), staleTime: Infinity });
export const useHistory = () => useQuery({ queryKey: ["history"], queryFn: () => api<{ events: EventOut[] }>("/history") });
export const useSettings = () => useQuery({ queryKey: ["settings"], queryFn: () => api<SettingsOut>("/settings") });

/** Runs list; polls every 3 s while a run is in progress (live status). */
export const useRuns = () =>
  useQuery({
    queryKey: ["runs"],
    queryFn: () => api<RunOut[]>("/runs"),
    refetchInterval: (q) => (q.state.data?.some((r) => r.status === "running") ? 3000 : 30000),
  });

export const useRunLog = (runId: number | null, live: boolean) =>
  useQuery({
    queryKey: ["runlog", runId],
    queryFn: () => api<LogLine[]>(`/runs/${runId}/log`),
    enabled: runId !== null,
    refetchInterval: live ? 3000 : false,
  });

export function useStartRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ started: boolean }>("/runs", { method: "POST" }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useSaveSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (days: number) => api<SettingsOut>("/settings", { method: "PUT", json: { days_between_runs: days } }),
    onSuccess: (data) => qc.setQueryData(["settings"], data),
  });
}
