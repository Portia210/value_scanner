import ReactECharts from "echarts-for-react";
import { useComputedColorScheme, useMantineTheme } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import type { StockRow } from "../api/client";
import { GURU_LABELS, GURU_ORDER, marketCapB, num, pct, score100, TYPE_LABELS } from "../format";

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

  const bySymbol = new Map(stocks.map((s) => [s.symbol, s]));
  const points = stocks
    .filter((s) => s.quality !== null && s.opportunity !== null)
    .map((s) => ({
      value: [s.quality!, s.opportunity!, marketCapB(s.market_cap)],
      name: s.symbol,
      inQuadrant: s.quality! >= qualityMin && s.opportunity! >= mosMin,
    }))
    // big circles first, so the small ones are drawn on top of them and never hidden
    .sort((a, b) => b.value[2] - a.value[2]);

  const option = {
    textStyle: { fontFamily: "Heebo" },
    grid: { left: 52, right: 24, top: 20, bottom: 48 },
    tooltip: {
      confine: true,
      extraCssText: "direction: rtl; text-align: right; max-width: 340px; white-space: normal;",
      formatter: (p: { name: string }) => {
        const s = bySymbol.get(p.name);
        return s ? tooltipHtml(s) : esc(p.name);
      },
    },
    xAxis: {
      name: "איכות (ציון קריטריונים)", nameLocation: "middle", nameGap: 30, min: 0, max: 1,
      nameTextStyle: { color: muted },
      axisLabel: { color: muted, formatter: (v: number) => Math.round(v * 100) },
      splitLine: { lineStyle: { color: grid } },
    },
    yAxis: {
      name: "מרווח ביטחון", nameLocation: "middle", nameGap: 40, min: -1, max: 1,
      nameTextStyle: { color: muted },
      axisLabel: { color: muted, formatter: (v: number) => `\u200E${Math.round(v * 100)}%` },
      splitLine: { lineStyle: { color: grid } },
    },
    series: [{
      type: "scatter",
      data: points.map((p) => ({
        ...p,
        // translucent fill + solid outline: overlapping circles stay distinguishable
        itemStyle: { color: `${p.inQuadrant ? pass : muted}${p.inQuadrant ? "aa" : "66"}`, borderColor: p.inQuadrant ? pass : muted, borderWidth: 1.5 },
        label: { show: p.inQuadrant || p.value[0] > 0.8 },
      })),
      symbolSize: (v: number[]) => Math.min(40, 9 + Math.sqrt(v[2]) * 1.2),
      label: { position: "top", formatter: "{b}", color: text, fontSize: 11, fontFamily: "JetBrains Mono" },
      emphasis: { scale: 1.3 },
      markArea: {
        silent: true,
        itemStyle: { color: pass, opacity: 0.08 },
        label: { show: true, position: "insideTopRight", formatter: "רבע הקנייה", color: pass },
        data: [[{ xAxis: qualityMin, yAxis: mosMin }, { xAxis: 1, yAxis: 1 }]],
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

/** Names come from a scraped site: never put them into HTML unescaped. */
const esc = (t: string | null | undefined): string =>
  (t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function tooltipHtml(s: StockRow): string {
  const row = (label: string, value: string) =>
    `<div style="display:flex;justify-content:space-between;gap:16px"><span style="opacity:.7">${label}</span><b dir="ltr">${value}</b></div>`;
  const rule = '<div style="border-top:1px solid rgba(128,128,128,.3);margin:6px 0"></div>';
  const types = s.labels.map((l) => TYPE_LABELS[l] ?? l).join(", ");
  const gurus = GURU_ORDER.map((g) => {
    const v = s.gurus[g];
    return row(GURU_LABELS[g], `${v.passed}/${v.computed} · ${score100(v.score)}`);
  }).join("");
  return `
    <div style="font-size:13px;line-height:1.5">
      <div style="font-size:15px"><b>${esc(s.symbol)}</b> ${s.candidate ? '<span style="color:#12b886">· מועמדת לקנייה</span>' : ""}</div>
      <div dir="ltr" style="text-align:right;opacity:.8">${esc(s.name)}</div>
      <div style="opacity:.7;margin-bottom:6px">${esc(s.sector)} · ${esc(s.industry)} · ${esc(types)}</div>
      ${row("איכות", score100(s.quality))}
      ${row("מרווח ביטחון", pct(s.opportunity))}
      ${rule}
      ${gurus}
      ${rule}
      ${row("מחיר", s.price === null ? "—" : `$${num(s.price)}`)}
      ${row("שווי שוק", s.market_cap === null ? "—" : `$${num(s.market_cap)}`)}
      ${row("P/E · P/B · P/S", `${num(s.pe_ratio, 1)} · ${num(s.pb_ratio, 1)} · ${num(s.ps_ratio, 1)}`)}
      <div style="opacity:.6;margin-top:4px">לחיצה פותחת את דף המניה</div>
    </div>`;
}
