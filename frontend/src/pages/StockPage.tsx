import { Anchor, Badge, Card, Grid, Group, RingProgress, SimpleGrid, Stack, Tabs, Text, Title } from "@mantine/core";
import { IconArrowRight } from "@tabler/icons-react";
import ReactECharts from "echarts-for-react";
import { Link, useParams } from "react-router-dom";
import { CriterionGauge } from "../components/CriterionGauge";
import { GuruBadge } from "../components/GuruBadge";
import { demoDetail } from "../mock/demo";
import { dirOf, GURU_LABELS, GURU_ORDER, pct, score100, TYPE_LABELS } from "../format";

export function StockPage() {
  const { symbol = "" } = useParams();
  const d = demoDetail(symbol.toUpperCase());
  if (!d) return <Text>המניה {symbol} לא נמצאה בריצה האחרונה.</Text>;

  const trend = {
    textStyle: { fontFamily: "Heebo" },
    legend: { top: 0 },
    grid: { left: 44, right: 44, top: 36, bottom: 28 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: d.series.years },
    yAxis: [{ type: "value", name: "EPS $" }, { type: "value", name: "%", splitLine: { show: false } }],
    series: [
      { name: "EPS", type: "bar", data: d.series.eps, itemStyle: { color: "#1f6de2", borderRadius: [4, 4, 0, 0] } },
      { name: "שולי רווח נקי", type: "line", yAxisIndex: 1, smooth: true, data: d.series.netMargin, itemStyle: { color: "#12b886" } },
      { name: "תשואה להון", type: "line", yAxisIndex: 1, smooth: true, data: d.series.roe, itemStyle: { color: "#fab005" } },
    ],
  };

  return (
    <Stack gap="lg">
      <Anchor component={Link} to="/" size="sm"><Group gap={4}><IconArrowRight size={14} />חזרה לדשבורד</Group></Anchor>
      <Group justify="space-between" align="center">
        <div>
          <Group gap="sm">
            <Title order={1} ff="monospace">{d.symbol}</Title>
            <Badge variant="default">{TYPE_LABELS[d.ctype]}</Badge>
            <Badge variant="light" color="gray" dir="ltr">{d.sector}</Badge>
          </Group>
          <Text c="dimmed" dir="ltr" ta="right">{d.name} · {d.industry}</Text>
          <Text size="xs" c="dimmed">נתונים נכון ל-{d.dataAsOf}</Text>
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
              {d.mos.map((m) => (
                <Group key={m.id} justify="space-between" py="xs" style={{ borderTop: "1px solid var(--mantine-color-default-border)" }} wrap="nowrap">
                  <div>
                    <Text size="sm">{m.title}</Text>
                    <Text size="xs" c="dimmed" ff="monospace" dir={dirOf(m.formula)} ta="right">{m.formula}</Text>
                  </div>
                  <Text ff="monospace" fw={600} dir="ltr" c={m.mos === null ? "dimmed" : m.mos >= 0.2 ? "teal" : m.mos < 0 ? "red" : undefined}>{pct(m.mos)}</Text>
                </Group>
              ))}
              <Text size="xs" c="dimmed" mt="xs">הציון הוא החציון של הרכיבים שרלוונטיים לסוג החברה.</Text>
            </Card>
            <Card>
              <Title order={4} mb="sm">מגמות 5 שנים</Title>
              <ReactECharts option={trend} style={{ height: 260 }} />
            </Card>
          </Stack>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
