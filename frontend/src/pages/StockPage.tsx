import { Alert, Anchor, Badge, Button, Card, Collapse, Divider, Grid, Group, Loader, RingProgress, SimpleGrid, Stack, Table, Tabs, Text, Title, UnstyledButton } from "@mantine/core";
import { IconArrowRight, IconCalendarEvent, IconChevronDown, IconChevronUp, IconDoorExit } from "@tabler/icons-react";
import ReactECharts from "echarts-for-react";
import { useComputedColorScheme } from "@mantine/core";
import { useEffect, useState } from "react";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { CriterionGauge } from "../components/CriterionGauge";
import { GuruBadge } from "../components/GuruBadge";
import { Prose, SourceLink } from "../components/Prose";
import { TickerAnalyzer } from "../components/TickerAnalyzer";
import { useProfileJob, useStartProfile, useStock, useStocks } from "../api/hooks";
import { ApiError, type StockDetail } from "../api/client";
import { FilterChanges } from "../components/FilterChanges";
import { asOf, dateTime, daysFromToday, localDay, updated, dirOf, EARNINGS_SOON_DAYS, fullDate, relativeDay, GURU_LABELS, GURU_ORDER, num, pct, REASON_LABELS, score100, TYPE_LABELS } from "../format";

export function StockPage() {
  const { symbol = "" } = useParams();
  const { data: d, isLoading, error } = useStock(symbol.toUpperCase());
  const dark = useComputedColorScheme("light") === "dark";
  const stockList = useStocks();
  const qualityMin = stockList.data?.quality_min ?? 0.7;
  const oppMin = stockList.data?.opportunity_min ?? 0.2;
  if (isLoading) return <Loader />;
  if (error instanceof ApiError && error.status === 404)
    return (
      <Stack>
        <Anchor component={Link} to="/">חזרה לדשבורד</Anchor>
        <Title order={3} ff="monospace">{symbol.toUpperCase()}</Title>
        <Text>עדיין אין ניתוח של המניה הזו. אפשר לנתח אותה עכשיו, גם אם היא לא עוברת את הסינון הראשוני.</Text>
        <TickerAnalyzer symbol={symbol.toUpperCase()} />
        <Anchor component={Link} to="/history" size="sm">אולי יצאה מהסינון? ראה כניסות ויציאות</Anchor>
      </Stack>
    );
  if (error || !d) return <Alert color="red">לא הצלחתי לטעון את המניה.</Alert>;

  const text = dark ? "#e0e0e0" : "#212529";
  const muted = dark ? "#adb5bd" : "#495057";
  const grid = dark ? "#444" : "#dee2e6";
  const BLUE = "#4c6ef5", GREEN = "#12b886", YELLOW = "#fab005";
  const trend = {
    textStyle: { fontFamily: "Heebo", color: muted },
    legend: { top: 0, textStyle: { color: text } },
    grid: { left: 52, right: 52, top: 44, bottom: 30 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: d.series.years, axisLabel: { color: muted } },
    yAxis: [
      { type: "value", name: "EPS ($)", nameTextStyle: { color: BLUE }, axisLabel: { color: BLUE },
        splitLine: { lineStyle: { color: grid } } },
      { type: "value", name: "אחוזים (%)", nameTextStyle: { color: muted }, axisLabel: { color: muted, formatter: "{value}%" },
        splitLine: { show: false } },
    ],
    series: [
      { name: "EPS מדולל ($)", type: "bar", data: d.series.eps, itemStyle: { color: BLUE, borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: "insideBottom", color: "#fff", fontSize: 11, formatter: (p: { value: number | null }) => (p.value === null ? "" : String(p.value)) } },
      { name: "שולי רווח נקי (%)", type: "line", yAxisIndex: 1, data: d.series.net_margin, symbolSize: 7,
        itemStyle: { color: GREEN }, lineStyle: { width: 2 },
        label: { show: true, position: "bottom", color: GREEN, fontSize: 10, fontWeight: "bold", formatter: (p: { value: number | null }) => (p.value === null ? "" : `\u200E${p.value}%`) } },
      { name: "תשואה להון, ROE (%)", type: "line", yAxisIndex: 1, data: d.series.roe, symbolSize: 7,
        itemStyle: { color: YELLOW }, lineStyle: { width: 2 },
        label: { show: true, position: "top", color: YELLOW, fontSize: 10, fontWeight: "bold", formatter: (p: { value: number | null }) => (p.value === null ? "" : `\u200E${p.value}%`) } },
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
        <Alert color="gray" icon={<IconDoorExit size={18} />}
          title={d.adhoc ? "ניתוח לפי טיקר: המניה אינה במעקב של הסריקה הרגילה" : "המניה אינה במעקב כרגע"}>
          <Stack gap="xs" align="flex-start">
            <Text size="sm">
              {d.adhoc
                ? `עדכני ${asOf(localDay(d.run.started_at))}.`
                : `היא יצאה מהסינון הראשוני. הנתונים בדף: ${updated(d.run.started_at)}.`}
              {" "}<Anchor component={Link} to="/history" size="sm">כניסות ויציאות</Anchor>
            </Text>
            <TickerAnalyzer symbol={d.symbol} reanalyse />
          </Stack>
        </Alert>
      )}
      {soon && snap?.next_earnings_date && <EarningsBanner symbol={d.symbol} day={snap.next_earnings_date} daysLeft={nextIn} />}
      <Group justify="space-between" align="center">
        <div>
          <Group gap="sm">
            <Title order={1} ff="monospace">{d.symbol}</Title>
            {d.labels.map((l) => <Badge key={l.label} variant="default" title={l.reason ?? undefined}>{TYPE_LABELS[l.label] ?? l.label}</Badge>)}
            {d.candidate && <Badge color="teal">מועמדת לקנייה</Badge>}
            <Badge variant="light" color="gray" dir="ltr">{d.sector}</Badge>
          </Group>
          <Text c="dimmed" dir="ltr" ta="right">{d.name} · {d.industry}{d.country ? ` · ${d.country}` : ""}</Text>
          <Text size="xs" c="dimmed">מחיר נכון {asOf(snap?.price_date)} · דוחות אחרונים: {relativeDay(snap?.last_earnings_date)}</Text>
          <Text size="xs" c="dimmed">
            {d.reports.have
              ? `הדוחות הכספיים כוללים תקופה שנסגרה ב-${fullDate(d.reports.have)}`
              : "התקופה האחרונה בדוחות עוד לא ידועה (תירשם בהורדה הבאה)"}
            {d.reports.downloaded_at ? ` · הורדו ${relativeDay(localDay(d.reports.downloaded_at))}` : ""}
          </Text>
          {d.reports.behind && d.reports.site && (
            <Text size="xs" c="orange" fw={700}>
              באתר כבר יש דוח לתקופה שנסגרה ב-{fullDate(d.reports.site)}; הוא ירד בריצה הבאה.
            </Text>
          )}
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

      {!d.profile && <ProfileButton symbol={d.symbol} />}
      {d.profile && <ProfileCard profile={d.profile} sic={d.sic_description} />}

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
              <Title order={4} mb={4}>מגמות לאורך שנות הכספים</Title>
              <Text size="xs" c="dimmed" mb="xs">
                עמודות כחולות: רווח למניה (EPS מדולל, בדולרים). קו ירוק: שולי רווח נקי, כלומר כמה אחוזים מההכנסות נשארו
                כרווח. קו צהוב: ROE, כלומר הרווח הנקי באחוזים מההון העצמי. הספרות מסומנות על כל נקודה.
              </Text>
              <ReactECharts option={trend} style={{ height: 300 }} notMerge />
            </Card>
            {(qHistory.length > 1 || oHistory.length > 1) && (
              <Card>
                <Title order={4} mb={4}>איך הציונים השתנו מריצה לריצה</Title>
                <Text size="xs" c="dimmed" mb="xs">
                  איכות: ממוצע ציוני הגורואים, 0 עד 100 (כמה קריטריונים עוברים ובאיזה מרווח).
                  מרווח ביטחון: כמה המחיר זול מהשווי ההוגן, באחוזים (שלילי = יקר מהשווי ההוגן).
                  כל נקודה היא ריצה אחת, והקווים המקווקווים הם הספים של "מועמדת לקנייה": צריך להיות מעליהם בשניהם.
                </Text>
                <ReactECharts style={{ height: 280 }} notMerge option={{
                  textStyle: { fontFamily: "Heebo", color: muted },
                  legend: { top: 0, textStyle: { color: text } },
                  tooltip: { trigger: "axis", valueFormatter: (v: number | null) => (v === null || v === undefined ? "—" : String(v)) },
                  grid: { left: 48, right: 84, top: 44, bottom: 56 },
                  xAxis: {
                    type: "category", name: "מתי חושב", nameLocation: "middle", nameGap: 40,
                    nameTextStyle: { color: muted }, axisLabel: { color: muted, lineHeight: 15 },
                    data: qHistory.map((h) => dateTime(h.started_at).replace(" ", "\n").replace(/\.\d{4}/, "")),
                  },
                  yAxis: { type: "value", axisLabel: { color: muted, formatter: (v: number) => `\u200E${v}` },
                    min: (v: { min: number }) => Math.floor((Math.min(v.min, 0) - 20) / 10) * 10,
                    max: (v: { max: number }) => Math.ceil((Math.max(v.max, 100) + 5) / 10) * 10,
                    splitLine: { lineStyle: { color: grid } } },
                  series: [
                    { name: "איכות (נקודות, 0 עד 100)", type: "line", symbolSize: 9, itemStyle: { color: BLUE },
                      label: { show: true, position: "top", color: BLUE, fontWeight: "bold" },
                      markLine: { silent: true, symbol: "none", lineStyle: { type: "dashed", color: BLUE, opacity: 0.6 },
                        label: { formatter: `סף איכות ${Math.round(qualityMin * 100)}`, color: BLUE, position: "insideEndTop" },
                        data: [{ yAxis: Math.round(qualityMin * 100) }] },
                      data: qHistory.map((h) => (h.score === null ? null : Math.round(h.score * 100))) },
                    { name: "מרווח ביטחון (אחוזים)", type: "line", symbolSize: 9, itemStyle: { color: GREEN },
                      label: { show: true, position: "top", color: GREEN, fontWeight: "bold", formatter: (p: { value: number | null }) => (p.value === null ? "" : `\u200E${p.value}%`) },
                      markLine: { silent: true, symbol: "none", lineStyle: { type: "dashed", color: GREEN, opacity: 0.6 },
                        label: { formatter: `סף מרווח ${Math.round(oppMin * 100)}%`, color: GREEN, position: "insideEndTop" },
                        data: [{ yAxis: Math.round(oppMin * 100) }] },
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
                  <Table.Td><FilterChanges detail={e.detail} /></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}

const PROFILE_OPEN_KEY = "profile-open";

function readOpen(): boolean {
  try { return localStorage.getItem(PROFILE_OPEN_KEY) === "1"; } catch { return false; }
}

/** "במשפט אחד": the one-line summary of the generated profile, shown while the card is folded. */
function oneLiner(text: string): string | null {
  const lines = text.split("\n");
  const i = lines.findIndex((l) => l.startsWith("## ") && l.includes("במשפט אחד"));
  if (i < 0) return null;
  const rest: string[] = [];
  for (const l of lines.slice(i + 1)) {
    if (l.startsWith("#") || /^-{3,}$/.test(l.trim())) break;
    if (l.trim()) rest.push(l.trim());
  }
  return rest.join(" ").replace(/\*\*/g, "") || null;
}

/** The company profile, foldable. Folded by default (it is long); the choice is remembered. */
function ProfileCard({ profile, sic }: { profile: NonNullable<StockDetail["profile"]>; sic: string | null }) {
  const [open, setOpen] = useState(readOpen);
  const toggle = () => {
    const next = !open;
    setOpen(next);
    try { localStorage.setItem(PROFILE_OPEN_KEY, next ? "1" : "0"); } catch { /* private mode */ }
  };
  const summary = oneLiner(profile.text);
  return (
    <Card>
      <UnstyledButton onClick={toggle} w="100%" aria-expanded={open} aria-label={open ? "הסתר את תיאור החברה" : "הצג את תיאור החברה"}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <div>
            <Title order={4}>על החברה</Title>
            <Text size="xs" c="dimmed">
              מבוסס על הדוח השנתי שהוגש ב-{profile.filing_date ? fullDate(profile.filing_date) : "—"} · סיכום AI, לא ייעוץ
              {sic ? ` · SIC: ${sic}` : ""}
            </Text>
          </div>
          <Group gap={4} wrap="nowrap">
            <Text size="sm" c="brand">{open ? "הסתר" : "הצג הכול"}</Text>
            {open ? <IconChevronUp size={18} /> : <IconChevronDown size={18} />}
          </Group>
        </Group>
      </UnstyledButton>
      {!open && summary && <Text size="sm" mt="xs" lineClamp={3}>{summary}</Text>}
      <Collapse in={open}>
        <Divider my="sm" />
        <Prose text={profile.text} />
        {profile.source_url && <SourceLink href={profile.source_url} />}
      </Collapse>
    </Card>
  );
}

const PROFILE_MESSAGES: Record<string, string> = {
  unsupported: "אין לחברה דוח שנתי מסוג 10-K או 20-F (למשל חברה קנדית שמגישה 40-F), ולכן אי אפשר ליצור לה תיאור.",
  failed: "יצירת התיאור נכשלה: חילוץ הפרקים מהדוח או הקריאה ל-Gemini. הפרטים נשמרו בהתראות.",
  billing: "בעיית חיוב בחשבון של Gemini (HTTP 402).",
};

/** Create the business profile on request (SEC annual report -> Gemini, about two minutes). */
function ProfileButton({ symbol }: { symbol: string }) {
  const start = useStartProfile();
  const qc = useQueryClient();
  const [waiting, setWaiting] = useState(false);
  const job = useProfileJob(symbol, waiting);
  const status = job.data?.status ?? "none";

  useEffect(() => {
    if (!waiting || status === "running" || status === "none") return;
    setWaiting(false);
    if (status === "ok") void qc.invalidateQueries({ queryKey: ["stock", symbol] });
  }, [waiting, status, symbol, qc]);

  const onClick = () =>
    start.mutate(symbol, {
      onSuccess: () => { setWaiting(true); void job.refetch(); },
      onError: (e) => {
        const code = e instanceof ApiError ? e.status : 0;
        const message =
          code === 503 ? "חסרה הגדרה בשרת (GOOGLE_API_KEY או MY_EMAIL)"
          : code === 404 || code === 405 ? "השרת רץ בגרסה ישנה מהממשק. הפעל מחדש את serve ורענן."
          : code === 409 ? "תיאור לחברה הזו כבר נוצר עכשיו"
          : "לא ניתן ליצור תיאור כרגע";
        notifications.show({ color: "red", message });
      },
    });

  const failed = !waiting && status !== "none" && status !== "running" && status !== "ok";
  return (
    <Card>
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Title order={4}>על החברה</Title>
          <Text size="xs" c="dimmed">
            עוד אין תיאור של החברה. אפשר ליצור אחד מהדוח השנתי שלה (סיכום AI, כשתי דקות).
          </Text>
          {failed && <Text size="sm" c="red" mt={4}>{PROFILE_MESSAGES[status] ?? "היצירה נכשלה."}</Text>}
        </div>
        <Button variant="light" loading={waiting || start.isPending} onClick={onClick}>
          {waiting ? "יוצר…" : failed ? "נסה שוב" : "צור תיאור חברה"}
        </Button>
      </Group>
    </Card>
  );
}

/** Orange banner for earnings less than 15 days away. Closable; the choice is kept per stock and date. */
function EarningsBanner({ symbol, day, daysLeft }: { symbol: string; day: string; daysLeft: number }) {
  const key = `earnings-closed:${symbol}:${day}`;
  const [closed, setClosed] = useState(() => {
    try { return localStorage.getItem(key) === "1"; } catch { return false; }
  });
  if (closed) return null;
  const when = daysLeft === 0 ? "היום" : daysLeft === 1 ? "מחר" : `בעוד ${daysLeft} ימים`;
  return (
    <Alert
      color="orange" variant="filled" icon={<IconCalendarEvent size={22} />}
      title={`דוחות רבעוניים ${when} · ${fullDate(day)}`}
      withCloseButton closeButtonLabel="סגור"
      onClose={() => {
        setClosed(true);
        try { localStorage.setItem(key, "1"); } catch { /* private mode: closes for this view only */ }
      }}
    >
      המחיר והמכפילים עלולים להשתנות משמעותית אחרי הפרסום, והנתונים בדף ישתנו בריצה הבאה.
    </Alert>
  );
}
