import { useEffect, useMemo, useState } from "react";
import {
  Alert, Avatar, Badge, Box, Card, Grid, Group, Loader, Progress, SegmentedControl, Select, SimpleGrid, Slider, Stack,
  Table, Text, TextInput, Title, UnstyledButton,
} from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { GuruBadge } from "../components/GuruBadge";
import { QualityOpportunityScatter } from "../components/QualityOpportunityScatter";
import { useStocks } from "../api/hooks";
import { dateTime, GURU_LABELS, GURU_ORDER, pct, primaryType, score100, TYPE_LABELS } from "../format";

function Kpi({ label, value, hint, accent }: { label: string; value: string; hint: string; accent?: boolean }) {
  return (
    <Card bg={accent ? "var(--mantine-color-teal-light)" : undefined}>
      <Text size="xs" c="dimmed" fw={600}>{label}</Text>
      <Text fz={32} fw={700} ff="monospace" c={accent ? "teal" : undefined} lh={1.3}>{value}</Text>
      <Text size="xs" c="dimmed">{hint}</Text>
    </Card>
  );
}

export function DashboardPage() {
  const { data, isLoading, error } = useStocks();
  const [qualityMin, setQualityMin] = useState(0.7);
  const [mosMin, setMosMin] = useState(0.2);
  const [sector, setSector] = useState<string | null>(null);
  const [ctype, setCtype] = useState<string>("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (data) { setQualityMin(data.quality_min); setMosMin(data.opportunity_min); }
  }, [data?.quality_min, data?.opportunity_min]); // eslint-disable-line react-hooks/exhaustive-deps

  const all = data?.stocks ?? [];
  const sectors = useMemo(() => [...new Set(all.map((s) => s.sector).filter((x): x is string => !!x))].sort(), [all]);

  if (isLoading) return <Loader />;
  if (error) return <Alert color="red">לא הצלחתי לטעון את הנתונים: {String(error)}</Alert>;
  if (!data?.run) return <Alert color="blue" title="אין עדיין נתונים">עוד לא הושלמה ריצה. אפשר להתחיל אחת במסך "ריצות".</Alert>;

  const filtered = all.filter((s) =>
    (!sector || s.sector === sector) &&
    (ctype === "all" || s.labels.includes(ctype) || (ctype === "regular" && s.labels.includes("regular"))) &&
    (!query || s.symbol.toLowerCase().includes(query.toLowerCase()) || (s.name ?? "").toLowerCase().includes(query.toLowerCase())));
  const isCandidate = (q: number | null, m: number | null) => q !== null && m !== null && q >= qualityMin && m >= mosMin;
  const candidates = filtered.filter((s) => isCandidate(s.quality, s.opportunity)).sort((a, b) => b.opportunity! - a.opportunity!);
  const ranked = [...filtered].sort((a, b) => (b.quality ?? -1) - (a.quality ?? -1));
  const unranked = all.filter((s) => s.quality === null).length;

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Text size="xs" c="dimmed">ריצה #{data.run.id} · {all.length} מניות במעקב · {dateTime(data.run.started_at)}</Text>
          <Title order={2}>מי עומדת בהכי הרבה קריטריונים, ובכמה היא זולה</Title>
        </div>
        <Group gap="xs" maw="100%">
          <TextInput leftSection={<IconSearch size={16} />} placeholder="חיפוש סימול או שם" value={query} onChange={(e) => setQuery(e.currentTarget.value)} w={220} aria-label="חיפוש מניה" />
          <Select placeholder="כל הסקטורים" data={sectors} value={sector} onChange={setSector} clearable w={200} />
          <Box maw="100%" style={{ overflowX: "auto" }}>
          <SegmentedControl
            value={ctype} onChange={setCtype}
            data={[{ value: "all", label: "הכול" }, ...["tech", "pharma", "cyclical", "regular", "financial"].map((t) => ({ value: t, label: TYPE_LABELS[t] }))]}
          />
          </Box>
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Kpi label="מניות במעקב" value={String(all.length)} hint={unranked ? `${unranked} בלי ציון איכות` : "כולן עם ציון איכות"} />
        <Kpi label={`איכות לפחות ${score100(qualityMin)}`} value={String(filtered.filter((s) => (s.quality ?? 0) >= qualityMin).length)} hint="ממוצע ציוני הגורואים" />
        <Kpi label={`מרווח ביטחון לפחות ${pct(mosMin, false)}`} value={String(filtered.filter((s) => (s.opportunity ?? -9) >= mosMin).length)} hint="חציון רכיבי ההזדמנות" />
        <Kpi label="מועמדות לקנייה" value={String(candidates.length)} hint="שני התנאים יחד" accent />
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <Card h="100%">
            <Group justify="space-between" mb="xs">
              <Title order={4}>איכות מול הזדמנות</Title>
              <Text size="xs" c="dimmed">גודל העיגול = שווי שוק · לחיצה פותחת את המניה</Text>
            </Group>
            <QualityOpportunityScatter stocks={filtered} qualityMin={qualityMin} mosMin={mosMin} />
            <SimpleGrid cols={2} mt="sm" spacing="xl">
              <Stack gap={4}>
                <Text size="xs" c="dimmed">סף איכות: <b>{score100(qualityMin)}</b></Text>
                <Slider min={0.3} max={0.95} step={0.05} value={qualityMin} onChange={setQualityMin} label={(v) => score100(v)} />
              </Stack>
              <Stack gap={4}>
                <Text size="xs" c="dimmed">סף מרווח ביטחון: <b dir="ltr">{pct(mosMin, false)}</b></Text>
                <Slider min={0} max={0.6} step={0.05} value={mosMin} onChange={setMosMin} label={(v) => pct(v, false)} />
              </Stack>
            </SimpleGrid>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 4 }}>
          <Card h="100%" p={0}>
            <Title order={4} p="lg" pb="xs">מועמדות לקנייה</Title>
            {candidates.length === 0 && <Text c="dimmed" size="sm" px="lg" pb="lg">אין מניות שעומדות בשני הספים. נסה להוריד את אחד מהם.</Text>}
            {candidates.map((s) => (
              <UnstyledButton key={s.symbol} component={Link} to={`/stocks/${s.symbol}`} px="lg" py="sm"
                style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}>
                <Group justify="space-between" wrap="nowrap">
                  <Group gap="sm" wrap="nowrap">
                    <Avatar color="teal" radius="md" ff="monospace">{s.symbol.slice(0, 2)}</Avatar>
                    <div>
                      <Text fw={600} ff="monospace">{s.symbol}</Text>
                      <Text size="xs" c="dimmed">{TYPE_LABELS[primaryType(s.labels)]} · <span dir="ltr">{s.sector}</span></Text>
                    </div>
                  </Group>
                  <div style={{ textAlign: "left" }}>
                    <Text fw={700} c="teal" ff="monospace" dir="ltr">{pct(s.opportunity)}</Text>
                    <Text size="xs" c="dimmed">איכות {score100(s.quality)}</Text>
                  </div>
                </Group>
              </UnstyledButton>
            ))}
          </Card>
        </Grid.Col>
      </Grid>

      <Card p={0}>
        <Group justify="space-between" p="lg" pb="sm">
          <Title order={4}>מטריצת קריטריונים</Title>
          <Text size="xs" c="dimmed">{ranked.length} מתוך {all.length} מניות</Text>
        </Group>
        <Table.ScrollContainer minWidth={820}>
          <Table highlightOnHover verticalSpacing="sm" horizontalSpacing="lg">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>מניה</Table.Th>
                <Table.Th>סוג</Table.Th>
                {GURU_ORDER.map((g) => <Table.Th key={g} ta="center">{GURU_LABELS[g]}</Table.Th>)}
                <Table.Th w="18%">איכות</Table.Th>
                <Table.Th ta="left">מרווח ביטחון</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {ranked.map((s) => (
                <Table.Tr key={s.symbol}>
                  <Table.Td>
                    <Text component={Link} to={`/stocks/${s.symbol}`} fw={600} ff="monospace" c="brand">{s.symbol}</Text>
                    <Text size="xs" c="dimmed" dir="ltr" ta="right">{s.name}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4}>{s.labels.map((l) => <Badge key={l} variant="default" radius="sm">{TYPE_LABELS[l] ?? l}</Badge>)}</Group>
                  </Table.Td>
                  {GURU_ORDER.map((g) => <Table.Td key={g} ta="center"><GuruBadge value={s.gurus[g]} label={GURU_LABELS[g]} /></Table.Td>)}
                  <Table.Td>
                    {s.quality === null ? <Text size="sm" c="dimmed">אין מספיק נתונים</Text> : (
                      <Group gap="xs" wrap="nowrap">
                        <Progress value={s.quality * 100} color={s.quality >= qualityMin ? "teal" : "gray"} flex={1} size="sm" />
                        <Text size="sm" ff="monospace" w={24}>{score100(s.quality)}</Text>
                      </Group>
                    )}
                  </Table.Td>
                  <Table.Td ta="left">
                    <Text ff="monospace" fw={600} dir="ltr" c={s.opportunity === null ? "dimmed" : s.opportunity >= mosMin ? "teal" : s.opportunity < 0 ? "red" : undefined}>
                      {pct(s.opportunity)}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {data.exited.length > 0 && (
        <Card>
          <Title order={4} mb={4}>יצאו מהמעקב</Title>
          <Text size="xs" c="dimmed" mb="sm">מניות שנותחו בריצה קודמת ואינן עוברות כרגע את הסינון. אפשר עדיין לפתוח את הדף שלהן (נתונים מהריצה האחרונה שבה נותחו).</Text>
          <Group gap="xs">
            {data.exited
              .filter((e) => !query || e.symbol.toLowerCase().includes(query.toLowerCase()) || (e.name ?? "").toLowerCase().includes(query.toLowerCase()))
              .map((e) => (
                <Badge key={e.symbol} component={Link} to={`/stocks/${e.symbol}`} variant="default" size="lg" radius="sm" style={{ cursor: "pointer" }} title={`${e.name ?? ""} · ריצה אחרונה #${e.last_run_id}`}>
                  <span style={{ fontFamily: "monospace" }}>{e.symbol}</span>
                </Badge>
              ))}
          </Group>
        </Card>
      )}
    </Stack>
  );
}
