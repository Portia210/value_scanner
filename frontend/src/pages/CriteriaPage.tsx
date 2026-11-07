import { Alert, Card, Loader, Stack, Table, Tabs, Text, Title } from "@mantine/core";
import { useCriteria } from "../api/hooks";
import { GURU_LABELS, GURU_ORDER, num } from "../format";

/** "How it is calculated": every criterion straight from the definitions in code (C10). */
export function CriteriaPage() {
  const { data, isLoading, error } = useCriteria();
  if (isLoading) return <Loader />;
  if (error || !data) return <Alert color="red">לא הצלחתי לטעון את הגדרות הקריטריונים.</Alert>;
  const byGuru = Object.fromEntries(data.gurus.map((g) => [g.guru, g]));

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>איך זה מחושב</Title>
        <Text c="dimmed" size="sm">הטבלאות נוצרות מההגדרות בקוד, כך שהן לא יכולות להיות שונות ממה שבפועל מחושב. שמות השורות והנוסחאות באנגלית בכוונה: הם שמות השורות באתר.</Text>
      </div>
      <Card>
        <Tabs defaultValue="graham">
          <Tabs.List>
            {GURU_ORDER.map((g) => <Tabs.Tab key={g} value={g}>{byGuru[g]?.title ?? GURU_LABELS[g]}</Tabs.Tab>)}
            <Tabs.Tab value="opportunity">הזדמנות וציון</Tabs.Tab>
          </Tabs.List>
          {GURU_ORDER.map((g) => (
            <Tabs.Panel key={g} value={g} pt="md">
              <Table.ScrollContainer minWidth={760}>
                <Table verticalSpacing="xs" horizontalSpacing="md">
                  <Table.Thead><Table.Tr><Table.Th>#</Table.Th><Table.Th>מבחן</Table.Th><Table.Th>נוסחה</Table.Th><Table.Th>סף</Table.Th><Table.Th>הערות</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>
                    {(byGuru[g]?.criteria ?? []).map((c, i) => (
                      <Table.Tr key={c.id}>
                        <Table.Td>{i + 1}</Table.Td>
                        <Table.Td dir="ltr" ta="right"><Text size="sm">{c.title}</Text><Text size="xs" c="dimmed" ff="monospace">{c.id}</Text></Table.Td>
                        <Table.Td dir="ltr" ta="right"><Text size="sm">{c.formula}</Text></Table.Td>
                        <Table.Td><Text size="sm" ff="monospace" dir="ltr" ta="right" style={{ whiteSpace: "nowrap" }}>{c.manual ? "בדיקה אנושית" : `${c.direction} ${num(c.threshold)}`}</Text></Table.Td>
                        <Table.Td dir="ltr" ta="right"><Text size="xs" c="dimmed">{c.note || "—"}</Text></Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Tabs.Panel>
          ))}
          <Tabs.Panel value="opportunity" pt="md">
            <Title order={4} mb="xs">רכיבי ציון ההזדמנות</Title>
            <Table verticalSpacing="xs" horizontalSpacing="md" mb="md">
              <Table.Tbody>
                {data.opportunity.map((c) => (
                  <Table.Tr key={c.id}><Table.Td dir="ltr" ta="right">{c.title}</Table.Td><Table.Td dir="ltr" ta="right"><Text size="sm" ff="monospace">{c.formula}</Text></Table.Td></Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            <Title order={4} mb="xs">איך הציון נבנה</Title>
            <Stack gap="xs">
              {data.scoring.map((block, i) => (
                <Text key={i} size="sm" style={{ whiteSpace: "pre-wrap" }}>{block.replace(/\*\*|`/g, "")}</Text>
              ))}
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Card>
    </Stack>
  );
}
