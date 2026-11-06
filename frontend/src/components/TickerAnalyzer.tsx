import { useEffect, useRef, useState } from "react";
import { Alert, Button, Group, Loader, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { IconChartBar } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAnalysis, useStartAnalysis } from "../api/hooks";

const STALE = "השרת רץ בגרסה ישנה מהממשק (חסרה לו היכולת הזו). הפעל מחדש את serve ורענן.";
/** What the server is doing, from the "phase=" code in the status message. */
function phaseText(message: string | null | undefined): string {
  const phase = message?.startsWith("phase=") ? message.slice(6) : "";
  if (phase === "fresh") return "הדוחות הכספיים עדכניים, לכן מעדכנים רק את המחיר והמכפילים.";
  if (phase.startsWith("statements:")) return `יש דוחות חדשים: מוריד ${phase.slice(11)} דוחות מהאתר, בקצב איטי בכוונה (עד כדקה).`;
  if (phase === "analysing") return "מחשב קריטריונים וציונים…";
  return "מושך מחיר ומכפילים עדכניים מהסורק…";
}

const REASONS: Record<number, string> = {
  409: "ריצה אחרת פועלת כרגע. נסה שוב בעוד כמה דקות.",
  429: "הגעת למגבלת הניתוחים היומית. נסה מחר.",
  422: "זה לא נראה כמו סימול של מניה.",
  404: STALE,
  405: STALE,
};

/**
 * Analyse any ticker on request (E8): starts a job on the server, shows its progress and opens
 * the stock page when it is done. `reanalyse` changes the wording for a stock that already has
 * an analysis.
 */
export function TickerAnalyzer({ symbol, reanalyse = false }: { symbol: string; reanalyse?: boolean }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [started, setStarted] = useState(false);
  const previous = useRef<string | null>(null);
  const status = useAnalysis(symbol, started);
  const start = useStartAnalysis();

  const s = status.data;
  // the run is "ours" once its start time differs from the one seen before the click
  const mine = started && !!s && !!s.started_at && s.started_at !== previous.current;
  const running = started && (!mine || s?.status === "running");
  const finished = mine && s && s.status !== "running";

  useEffect(() => {
    if (finished && s?.status === "ok") {
      void qc.invalidateQueries({ queryKey: ["stock", symbol] });
      void qc.invalidateQueries({ queryKey: ["stocks"] });
      navigate(`/stocks/${symbol}`);
    }
  }, [finished, s?.status, symbol, navigate, qc]);

  const onClick = () => {
    previous.current = s?.started_at ?? null;
    start.mutate(symbol, {
      onSuccess: () => setStarted(true),
      onError: (e) =>
        notifications.show({
          color: "red",
          message: e instanceof ApiError ? (REASONS[e.status] ?? `שגיאה: ${e.message}`) : "שגיאה בהתחלת הניתוח",
        }),
    });
  };

  if (running)
    return (
      <Group gap="sm">
        <Loader size="sm" />
        <Stack gap={0}>
          <Text size="sm" fw={600}>מנתח את <span dir="ltr">{symbol}</span>…</Text>
          <Text size="xs" c="dimmed">
            {phaseText(mine ? s?.message : null)}
            {mine && s?.progress_total ? ` (${s.progress_done}/${s.progress_total})` : ""}
          </Text>
        </Stack>
      </Group>
    );

  return (
    <Stack gap="xs" align="flex-start">
      {finished && s?.status !== "ok" && (
        <Alert color={s?.status === "blocked" ? "orange" : "red"} py={6}>
          {s?.status === "blocked" ? "האתר חסם את הבקשה, נסה שוב מאוחר יותר." : `הניתוח נכשל: ${s?.message ?? "שגיאה לא ידועה"}`}
        </Alert>
      )}
      <Button leftSection={<IconChartBar size={16} />} onClick={onClick} loading={start.isPending}
        variant={reanalyse ? "light" : "filled"} size={reanalyse ? "xs" : "sm"}>
        {reanalyse ? "נתח מחדש" : <>נתח את <span dir="ltr">&nbsp;{symbol}&nbsp;</span> לפי כל הקריטריונים</>}
      </Button>
      {!reanalyse && (
        <Text size="xs" c="dimmed">
          מושך מחיר ומכפילים עדכניים, מוריד דוחות כספיים רק אם אין לה או אם הופיעו חדשים, ומריץ את כל הגורואים. לא משפיע על הסריקה הרגילה.
          {s ? ` נשארו ${s.analyses_left_today} ניתוחים היום.` : ""}
        </Text>
      )}
    </Stack>
  );
}
