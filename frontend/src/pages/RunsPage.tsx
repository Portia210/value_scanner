import { useState } from "react";
import { Badge, Button, Card, Grid, Group, NumberInput, Progress, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlayerPlay } from "@tabler/icons-react";
import { demoRuns, demoSettings } from "../mock/demo";
import type { RunInfo } from "../types";

const STATUS: Record<RunInfo["status"], { label: string; color: string }> = {
  running: { label: "רצה", color: "blue" },
  succeeded: { label: "הצליחה", color: "teal" },
  failed: { label: "נכשלה", color: "red" },
  interrupted: { label: "נקטעה", color: "yellow" },
};

export function RunsPage() {
  const [interval, setInterval] = useState<number | string>(demoSettings.intervalDays);
  const running = demoRuns.find((r) => r.status === "running");

  return (
    <Stack gap="lg">
      <Title order={2}>ריצות והגדרות</Title>
      <Grid>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card h="100%">
            <Title order={4} mb="md">תזמון</Title>
            <NumberInput label="ריצה מלאה כל" suffix=" ימים" min={1} max={60} value={interval} onChange={setInterval} w={200} />
            <Text size="xs" c="dimmed" mt={4}>עדכון מחירים רץ כל יום ב-03:00, בנפרד מהריצה המלאה.</Text>
            <Group mt="lg">
              <Button onClick={() => notifications.show({ message: "ההגדרות נשמרו (דמה)", color: "teal" })}>שמירה</Button>
              <Button variant="light" leftSection={<IconPlayerPlay size={16} />} disabled={!!running}>
                {running ? "ריצה כבר פועלת" : "הרץ כעת"}
              </Button>
            </Group>
            <Text size="sm" mt="lg">ריצה מלאה הבאה: <b>08.11.2026 03:00</b></Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card h="100%">
            <Title order={4} mb="md">ריצה נוכחית</Title>
            {running ? (
              <Stack gap="xs">
                <Group justify="space-between"><Text>ריצה #{running.id} · התחילה {running.startedAt}</Text><Badge color="blue">רצה</Badge></Group>
                <Progress value={(running.ok / 110) * 100} size="lg" animated striped />
                <Text size="sm" c="dimmed">{running.ok} מתוך 110 מניות · מוריד כרגע: <span dir="ltr">LULU / ratios</span></Text>
                <Text size="sm" c="dimmed">קצב: בקשה כל 3–6 שניות · הפסקה ארוכה כל 25 בקשות · 0 חסימות</Text>
              </Stack>
            ) : <Text c="dimmed">אין ריצה פעילה.</Text>}
          </Card>
        </Grid.Col>
      </Grid>
      <Card p={0}>
        <Title order={4} p="lg" pb="sm">היסטוריה</Title>
        <Table verticalSpacing="sm" horizontalSpacing="lg" highlightOnHover>
          <Table.Thead>
            <Table.Tr><Table.Th>#</Table.Th><Table.Th>סוג</Table.Th><Table.Th>הופעלה ע"י</Table.Th><Table.Th>התחילה</Table.Th><Table.Th>משך</Table.Th><Table.Th>מניות</Table.Th><Table.Th>סטטוס</Table.Th></Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {demoRuns.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td ff="monospace">{r.id}</Table.Td>
                <Table.Td>{r.kind === "full" ? "מלאה" : "מחירים"}</Table.Td>
                <Table.Td>{r.trigger === "manual" ? "ידני" : "תזמון"}</Table.Td>
                <Table.Td ff="monospace">{r.startedAt}</Table.Td>
                <Table.Td>{r.durationMin === null ? "—" : `${r.durationMin} דק'`}</Table.Td>
                <Table.Td ff="monospace">{r.ok}{r.failed ? <Text span c="red"> / {r.failed} נכשלו</Text> : null}</Table.Td>
                <Table.Td><Badge variant="light" color={STATUS[r.status].color}>{STATUS[r.status].label}</Badge></Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
