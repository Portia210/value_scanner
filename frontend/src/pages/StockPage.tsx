import { Alert, Anchor, Badge, Card, Grid, Group, Loader, RingProgress, SimpleGrid, Spoiler, Stack, Table, Tabs, Text, Title } from "@mantine/core";
import { IconArrowRight, IconCalendarEvent, IconDoorExit } from "@tabler/icons-react";
import ReactECharts from "echarts-for-react";
import { useComputedColorScheme } from "@mantine/core";
import { Link, useParams } from "react-router-dom";
import { CriterionGauge } from "../components/CriterionGauge";
import { GuruBadge } from "../components/GuruBadge";
import { Prose, SourceLink } from "../components/Prose";
import { useStock } from "../api/hooks";
import { ApiError } from "../api/client";
import { asOf, dateTime, daysFromToday, dirOf, EARNINGS_SOON_DAYS, fullDate, relativeDay, FILTER_LABELS, GURU_LABELS, GURU_ORDER, num, pct, REASON_LABELS, score100, TYPE_LABELS } from "../format";

export function StockPage() {
  const { symbol = "" } = useParams();
  const { data: d, isLoading, error } = useStock(symbol.toUpperCase());
  const dark = useComputedColorScheme("light") === "dark";
  if (isLoading) return <Loader />;
  if (error instanceof ApiError && error.status === 404)
    return (
      <Stack>
        <Anchor component={Link} to="/">חזרה לדשבורד</Anchor>
        <Text>המניה {symbol} אינה במעקב בריצה האחרונה (לא עוברת כרגע את הסינון הראשוני, או שאינה מוכרת).</Text>
        <Anchor component={Link} to="/history" size="sm">אולי יצאה מהסינון: ראה כניסות ויציאות</Anchor>
      </Stack>
    );
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
  const nextIn = daysFromToday(snap?.next_earnings_date);
  const soon = nextIn !== null && nextIn >= 0 && nextIn < EARNINGS_SOON_DAYS;

  return (
    <Stack gap="lg">
      <Anchor component={Link} to="/" size="sm"><Group gap={4}><IconArrowRight size={14} />חזרה לדשבורד</Group></Anchor>
      {d.in_latest_run === false && (
        <Alert color="gray" icon={<IconDoorExit size={18} />} title="המניה אינה במעקב כרגע">
          היא יצאה מהסינון הראשוני. הנתונים בדף הם מריצה #{d.run.id}, האחרונה שבה נותחה.
          {" "}<Anchor component={Link} to="/history" size="sm">למה יצאה? ראה כניסות ויציאות</Anchor>
        </Alert>
      )}
      {soon && snap?.next_earnings_date && (
        <Alert color="orange" variant="filled" icon={<IconCalendarEvent size={22} />} title={`דוחות רבעוניים ${nextIn === 0 ? "היום" : nextIn === 1 ? "מחר" : `בעוד ${nextIn} ימים`} · ${fullDate(snap.next_earnings_date)}`}>
          המחיר והמכפילים עלולים להשתנות משמעותית אחרי הפרסום, והנתונים בדף ישתנו בריצה הבאה.
        </Alert>
      )}
      <Group justify="space-between" align="center">
        <div>
          <Group gap="sm">
            <Title order={1} ff="monospace">{d.symbol}</Title>
            {d.labels.map((l) => <Badge key={l.label} variant="default" title={l.reason ?? undefined}>{TYPE_LABELS[l.label] ?? l.label}</Badge>)}
            {d.candidate && <Badge color="teal">מועמדת לקנייה</Badge>}
            <Badge variant="light" color="gray" dir="ltr">{d.sector}</Badge>
          </Group>
          <Text c="dimmed" dir="ltr" ta="right">{d.name} · {d.industry}{d.country ? ` · ${d.country}` : ""}</Text>
          <Text size="xs" c="dimmed">ריצה #{d.run.id} · מחיר נכון {asOf(snap?.price_date)} · דוחות אחרונים: {relativeDay(snap?.last_earnings_date)}</Text>
          {snap?.next_earnings_date && (
            <Text size="xs" c={soon ? "orange" : "dimmed"} fw={soon ? 700 : 400}>
              דוחות הבאים: {relativeDay(snap.next_earnings_date)}{nextIn !== null && nextIn > 1 && nextIn < 60 ? ` (בעוד ${nextIn} ימים)` : ""}
            </Text>
          )}
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

      {d.profile && (
        <Card>
          <Group justify="space-between" mb="xs" align="baseline">
            <Title order={4}>על החברה</Title>
            <Text size="xs" c="dimmed">
              מבוסס על הדוח השנתי שהוגש ב-{d.profile.filing_date ? fullDate(d.profile.filing_date) : "—"} · סיכום AI, לא ייעוץ
              {d.sic_description ? ` · SIC: ${d.sic_description}` : ""}
            </Text>
          </Group>
          <Spoiler maxHeight={320} showLabel="הצג הכול" hideLabel="הסתר">
            <Prose text={d.profile.text} />
          </Spoiler>
          {d.profile.source_url && <SourceLink href={d.profile.source_url} />}
        </Card>
      )}

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
                <Title order={4} mb={4}>איך הציונים השתנו מריצה לריצה</Title>
                <Text size="xs" c="dimmed" mb="xs">
                  איכות: ממוצע ציוני הגורואים, 0 עד 100 (כמה קריטריונים עוברים ובאיזה מרווח).
                  מרווח ביטחון: כמה המחיר זול מהשווי ההוגן, באחוזים (שלילי = יקר מהשווי ההוגן).
                  כל נקודה היא ריצה אחת.
                </Text>
                <ReactECharts style={{ height: 240 }} notMerge option={{
                  textStyle: { fontFamily: "Heebo", color: dark ? "#c9c9c9" : "#495057" },
                  legend: { top: 0, textStyle: { color: dark ? "#e0e0e0" : "#212529" } },
                  tooltip: { trigger: "axis", valueFormatter: (v: number | null) => (v === null || v === undefined ? "—" : String(v)) },
                  grid: { left: 48, right: 24, top: 40, bottom: 44 },
                  xAxis: {
                    type: "category", name: "ריצה (תאריך)", nameLocation: "middle", nameGap: 28,
                    data: qHistory.map((h) => `#${h.run_id} · ${dateTime(h.started_at).slice(0, 5)}`),
                  },
                  yAxis: { type: "value",
                    splitLine: { lineStyle: { color: dark ? "#444" : "#dee2e6" } } },
                  series: [
                    { name: "איכות, 0 עד 100", type: "line", symbolSize: 8, itemStyle: { color: "#4c6ef5" },
                      data: qHistory.map((h) => (h.score === null ? null : Math.round(h.score * 100))) },
                    { name: "מרווח ביטחון, באחוזים", type: "line", symbolSize: 8, itemStyle: { color: "#51cf66" },
                      data: oHistory.map((h) => (h.score === null ? null : Math.round(h.score * 100))) },
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
