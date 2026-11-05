import ReactECharts from "echarts-for-react";
import { useComputedColorScheme, useMantineTheme } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import type { StockRow } from "../types";

interface Props {
  stocks: StockRow[];
  qualityMin: number;
  mosMin: number;
  height?: number;
}

/** Quality (x) vs margin of safety (y); the top-right "buy quadrant" is shaded. Click a dot to open the stock. */
export function QualityOpportunityScatter({ stocks, qualityMin, mosMin, height = 380 }: Props) {
  const theme = useMantineTheme();
  const scheme = useComputedColorScheme("light");
  const navigate = useNavigate();
  const dark = scheme === "dark";
  const muted = dark ? theme.colors.dark[2] : theme.colors.gray[6];
  const grid = dark ? theme.colors.dark[4] : theme.colors.gray[2];
  const text = dark ? theme.colors.dark[0] : theme.colors.dark[7];
  const pass = theme.colors.teal[6];

  const points = stocks
    .filter((s) => s.quality !== null && s.opportunity !== null)
    .map((s) => ({
      value: [s.quality!, s.opportunity!, s.marketCapB],
      name: s.symbol,
      inQuadrant: s.quality! >= qualityMin && s.opportunity! >= mosMin,
    }));

  const option = {
    textStyle: { fontFamily: "Heebo" },
    grid: { left: 52, right: 24, top: 20, bottom: 48 },
    tooltip: {
      formatter: (p: { name: string; value: number[] }) =>
        `<b>${p.name}</b><br/>איכות ${Math.round(p.value[0] * 100)} · מרווח ביטחון ${Math.round(p.value[1] * 100)}%`,
    },
    xAxis: {
      name: "איכות (ציון קריטריונים)", nameLocation: "middle", nameGap: 30, min: 0.3, max: 1,
      nameTextStyle: { color: muted },
      axisLabel: { color: muted, formatter: (v: number) => Math.round(v * 100) },
      splitLine: { lineStyle: { color: grid } },
    },
    yAxis: {
      name: "מרווח ביטחון", nameLocation: "middle", nameGap: 40, min: -0.6, max: 0.5,
      nameTextStyle: { color: muted },
      axisLabel: { color: muted, formatter: (v: number) => `${Math.round(v * 100)}%` },
      splitLine: { lineStyle: { color: grid } },
    },
    series: [{
      type: "scatter",
      data: points.map((p) => ({
        ...p,
        itemStyle: { color: p.inQuadrant ? pass : muted, opacity: p.inQuadrant ? 0.95 : 0.55 },
        label: { show: p.inQuadrant || p.value[0] > 0.8 },
      })),
      symbolSize: (v: number[]) => 9 + Math.sqrt(v[2]) * 2.2,
      label: { position: "top", formatter: "{b}", color: text, fontSize: 11, fontFamily: "JetBrains Mono" },
      emphasis: { scale: 1.3 },
      markArea: {
        silent: true,
        itemStyle: { color: pass, opacity: 0.08 },
        label: { show: true, position: "insideTopRight", formatter: "רבע הקנייה", color: pass },
        data: [[{ xAxis: qualityMin, yAxis: mosMin }, { xAxis: 1, yAxis: 0.5 }]],
      },
      markLine: {
        silent: true, symbol: "none", label: { show: false },
        lineStyle: { type: "dashed", color: muted, opacity: 0.6 },
        data: [{ xAxis: qualityMin }, { yAxis: mosMin }, { yAxis: 0 }],
      },
    }],
  };

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      notMerge
      onEvents={{ click: (p: { name: string }) => navigate(`/stocks/${p.name}`) }}
    />
  );
}
