import ReactECharts from "echarts-for-react";
import { useComputedColorScheme, useMantineTheme } from "@mantine/core";

export interface TimelineEvent {
  symbol: string;
  direction: string; // "enter" | "exit"
  created_at: string;
}

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const p2 = (n: number) => String(n).padStart(2, "0");
const dayKey = (iso: string) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
};
const dayLabel = (key: string) => `${key.slice(8, 10)}.${key.slice(5, 7)}`;

/**
 * E6 timeline: one column per day. Above the axis the stocks that entered the screen that day,
 * below it the ones that left. Hover a column to see which stocks.
 */
export function EntryExitTimeline({ events, height = 240 }: { events: TimelineEvent[]; height?: number }) {
  const theme = useMantineTheme();
  const dark = useComputedColorScheme("light") === "dark";
  const muted = dark ? theme.colors.dark[2] : theme.colors.gray[6];
  const grid = dark ? theme.colors.dark[4] : theme.colors.gray[2];

  const days = new Map<string, { enter: string[]; exit: string[] }>();
  for (const e of events) {
    const k = dayKey(e.created_at);
    const d = days.get(k) ?? { enter: [], exit: [] };
    (e.direction === "enter" ? d.enter : d.exit).push(e.symbol);
    days.set(k, d);
  }
  const keys = [...days.keys()].sort();
  if (keys.length === 0) return null;

  const option = {
    textStyle: { fontFamily: "Heebo" },
    grid: { left: 44, right: 16, top: 16, bottom: 44 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
      extraCssText: "direction: rtl; text-align: right; max-width: 320px; white-space: normal;",
      formatter: (params: { dataIndex: number }[]) => {
        const k = keys[params[0].dataIndex];
        const d = days.get(k)!;
        const line = (label: string, list: string[]) =>
          list.length ? `<div>${label}: <b dir="ltr">${list.map(esc).join(", ")}</b></div>` : "";
        return `<div>${esc(dayLabel(k))}.${k.slice(0, 4)}</div>${line("נכנסו", d.enter)}${line("יצאו", d.exit)}`;
      },
    },
    xAxis: {
      type: "category", data: keys.map(dayLabel), name: "תאריך", nameLocation: "middle", nameGap: 28,
      nameTextStyle: { color: muted }, axisLabel: { color: muted }, axisLine: { lineStyle: { color: grid } },
    },
    yAxis: {
      type: "value", name: "מניות", nameTextStyle: { color: muted }, minInterval: 1,
      axisLabel: { color: muted, formatter: (v: number) => String(Math.abs(v)) },
      splitLine: { lineStyle: { color: grid } },
    },
    series: [
      { name: "נכנסו", type: "bar", stack: "t", barMaxWidth: 36, itemStyle: { color: theme.colors.teal[6] },
        data: keys.map((k) => days.get(k)!.enter.length) },
      { name: "יצאו", type: "bar", stack: "t", barMaxWidth: 36, itemStyle: { color: theme.colors.red[6] },
        data: keys.map((k) => -days.get(k)!.exit.length) },
    ],
  };
  return <ReactECharts option={option} style={{ height }} notMerge />;
}
