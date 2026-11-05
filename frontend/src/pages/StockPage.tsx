import { Alert, Anchor, Badge, Card, Grid, Group, Loader, RingProgress, SimpleGrid, Stack, Table, Tabs, Text, Title } from "@mantine/core";
import { IconArrowRight } from "@tabler/icons-react";
import ReactECharts from "echarts-for-react";
import { Link, useParams } from "react-router-dom";
import { CriterionGauge } from "../components/CriterionGauge";
import { GuruBadge } from "../components/GuruBadge";
import { useStock } from "../api/hooks";
import { ApiError } from "../api/client";
import { date, dateTime, dirOf, FILTER_LABELS, GURU_LABELS, GURU_ORDER, num, pct, REASON_LABELS, score100, TYPE_LABELS } from "../format";

export function StockPage() {
  const { symbol = "" } = useParams();
  const { data: d, isLoading, error } = useStock(symbol.toUpperCase());
  if (isLoading) return <Loader />;
  if (error instanceof ApiError && error.status === 404)
    return <Stack><Anchor component={Link} to="/">חזרה לדשבורד</Anchor><Text>המניה {symbol} לא נותחה בריצה האחרונה (היא לא עברה את הסינון הראשוני).</Text></Stack>;
  if (error || !d) return <Alert color="red">לא הצלחתי לטעון את המניה.</Alert>;

  const trend = {
    textStyle: { fontFamily: "Heebo" },
    legend: { top: 0 },
    grid: { left: 44, right: 44, top: 36, bottom: 28 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: d.series.years },
    yAxis: [{ type: "value", name: "EPS $" }, { type: "value", name: "%", splitLine: { show: false } }],
    series: [
      { name: "EPS", type: "bar", data: d.series.eps, itemStyle: { color: "#1f6de2", borderRadius: [4, 4, 0, 0] } },
      { name: "שולי רווח נקי", type: "line", yAxisIndex: 1, smooth: true, data: d.series.net_margin, itemStyle: { color: "#12b886" } },
      { name: "ROE", type: "line", yAxisIndex: 1, smooth: true, data: d.series.roe, itemStyle: { color: "#fab005" } },
    ],
  };
  const qHistory = d.history.quality ?? [];
  const oHistory = d.history.opportunity ?? [];
  const snap = d.snapshot;

  return (
    <Stack gap="lg">
      <Anchor component={Link} to="/" size="sm"><Group gap={4}><IconArrowRight size={14} />חזרה לדשבורד</Group></Anchor>
      <Group justify="space-between" align="center">
        <div>
          <Group gap="sm">
            <Title order={1} ff="monospace">{d.symbol}</Title>
            {d.labels.map((l) => <Badge key={l.label} variant="default" title={l.reason ?? undefined}>{TYPE_LABELS[l.label] ?? l.label}</Badge>)}
            {d.candidate && <Badge color="teal">מועמדת לקנייה</Badge>}
            <Badge variant="light" color="gray" dir="ltr">{d.sector}</Badge>
          </Group>
          <Text c="dimmed" dir="ltr" ta="right">{d.name} · {d.industry}{d.country ? ` · ${d.country}` : ""}</Text>
          <Text size="xs" c="dimmed">ריצה #{d.run.id} · מחיר נכון ל-{date(snap?.price_date)} · דוחות אחרונים: {date(snap?.last_earnings_date)}</Text>
        </div>
        <Group gap="xl">
          <Stack align="center" gap={0}>
            <RingProgress size={96} thickness={9} roundCaps sections={[{ value: (d.quality ?? 0) * 100, color: "teal" }]}
              label={<Text ta="center" fw={700} ff="monospace">{score100(d.quality)}</Text>} />
            <Text size="sm" c="dimmed">איכות</Text>
          </Stack>
          <Stack align="center" gap={0}>
            <Text fz={34} fw={700} ff="monospace" c={(d.opportunity ?? 0) >= 0.2 ? "teal" : undefined} dir="ltr">{pct(d.opportunity)}</Text>
            <Text size="sm" c="dimmed">מרווח ביטחון</Text>
          </Stack>
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 2, md: 4 }}>
        {GURU_ORDER.map((g) => (
          <Card key={g} p="md">
            <Group justify="space-between">
              <Text fw={600}>{GURU_LABELS[g]}</Text>
              <GuruBadge value={d.gurus[g]} label={GURU_LABELS[g]} />
            </Group>
            <Text size="xs" c="dimmed" mt={4}>ציון {score100(d.gurus[g].score)} · כיסוי {score100(d.gurus[g].coverage)}%</Text>
          </Card>
        ))}
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <Card>
            <Title order={4} mb="sm">כל קריטריון מול הסף</Title>
            <Tabs defaultValue="graham">
              <Tabs.List>
                {GURU_ORDER.map((g) => <Tabs.Tab key={g} value={g}>{GURU_LABELS[g]}</Tabs.Tab>)}
              </Tabs.List>
              {GURU_ORDER.map((g) => (
                <Tabs.Panel key={g} value={g} pt="xs">
                  {d.criteria.filter((c) => c.guru === g).map((c) => <CriterionGauge key={c.id} c={c} />)}
                </Tabs.Panel>
              ))}
            </Tabs>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 5 }}>
          <Stack>
            <Card>
              <Title order={4} mb="sm">ממה מורכב מרווח הביטחון</Title>
              {d.components.map((m) => (
                <Group key={m.id} justify="space-between" py="xs" style={{ borderTop: "1px solid var(--mantine-color-default-border)" }} wrap="nowrap">
                  <div>
                    <Text size="sm" dir="ltr" ta="right">{m.title}</Text>
                    <Text size="xs" c="dimmed" ff="monospace" dir={dirOf(m.formula)} ta="right">{m.formula}</Text>
                  </div>
                  <Text ff="monospace" fw={600} dir="ltr" style={{ whiteSpace: "nowrap" }} c={m.value === null ? "dimmed" : m.value >= 0.2 ? "teal" : m.value < 0 ? "red" : undefined}>
                    {m.value === null ? "לא חל" : pct(m.value)}
                  </Text>
                </Group>
              ))}
              <Text size="xs" c="dimmed" mt="xs">הציון הוא החציון של הרכיבים שחלים על המניה.</Text>
              {snap && (
                <Text size="xs" c="dimmed" mt="xs" dir="ltr" ta="right">
                  P/E {num(snap.pe_ratio)} · P/B {num(snap.pb_ratio)} · P/S {num(snap.ps_ratio)} · P/E 5Y {num(snap.pe_ratio_5y)} · mkt cap {num(snap.market_cap)}
                </Text>
              )}
            </Card>
            <Card>
              <Title order={4} mb="sm">מגמות (שנות FY)</Title>
              <ReactECharts option={trend} style={{ height: 260 }} />
            </Card>
            {(qHistory.length > 1 || oHistory.length > 1) && (
              <Card>
                <Title order={4} mb="sm">ציון לאורך ריצות</Title>
                <ReactECharts style={{ height: 200 }} option={{
                  textStyle: { fontFamily: "Heebo" }, legend: { top: 0 }, tooltip: { trigger: "axis" },
                  grid: { left: 40, right: 20, top: 36, bottom: 24 },
                  xAxis: { type: "category", data: qHistory.map((h) => `#${h.run_id}`) },
                  yAxis: { type: "value" },
                  series: [
                    { name: "איכות", type: "line", data: qHistory.map((h) => h.score) },
                    { name: "הזדמנות", type: "line", data: oHistory.map((h) => h.score) },
                  ],
                }} />
              </Card>
            )}
          </Stack>
        </Grid.Col>
      </Grid>

      <Card p={0}>
        <Title order={4} p="lg" pb="sm">כניסות ויציאות מהמעקב</Title>
        {d.events.length === 0 ? <Text c="dimmed" size="sm" px="lg" pb="lg">אין אירועים רשומים למניה הזו (היא במעקב מהריצה הראשונה).</Text> : (
          <Table verticalSpacing="xs" horizontalSpacing="lg">
            <Table.Tbody>
              {d.events.map((e) => (
                <Table.Tr key={e.id}>
                  <Table.Td>{dateTime(e.created_at)}</Table.Td>
                  <Table.Td><Badge color={e.direction === "enter" ? "teal" : "red"} variant="light">{e.direction === "enter" ? "נכנסה" : "יצאה"}</Badge></Table.Td>
                  <Table.Td>{REASON_LABELS[e.reason_type] ?? e.reason_type}</Table.Td>
                  <Table.Td dir="ltr" ta="right">
                    {Object.entries((e.detail ?? {}) as Record<string, { before: number | null; after: number | null }>)
                      .filter(([, v]) => v && typeof v === "object" && "after" in v)
                      .map(([k, v]) => `${FILTER_LABELS[k] ?? k}: ${num(v.before)} → ${num(v.after)}`).join(" · ")}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
