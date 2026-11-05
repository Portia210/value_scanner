import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Code, Grid, Group, NumberInput, Progress, ScrollArea, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlayerPlay } from "@tabler/icons-react";
import { ApiError } from "../api/client";
import { useRunLog, useRuns, useSaveSettings, useSettings, useStartRun } from "../api/hooks";
import { dateTime } from "../format";

const STATUS: Record<string, { label: string; color: string }> = {
  running: { label: "רצה", color: "blue" },
  ok: { label: "הצליחה", color: "teal" },
  failed: { label: "נכשלה", color: "red" },
  blocked: { label: "נחסמה", color: "orange" },
  interrupted: { label: "נקטעה", color: "yellow" },
};
const KIND: Record<string, string> = { scheduled: "תזמון", manual: "ידני", cli: "שורת פקודה" };

export function RunsPage() {
  const runs = useRuns();
  const settings = useSettings();
  const save = useSaveSettings();
  const start = useStartRun();
  const [days, setDays] = useState<number | string>(7);
  const [selected, setSelected] = useState<number | null>(null);

  const list = runs.data ?? [];
  const running = list.find((r) => r.status === "running");
  const logRunId = selected ?? running?.id ?? list[0]?.id ?? null;
  const log = useRunLog(logRunId, !!running && logRunId === running.id);

  useEffect(() => { if (settings.data) setDays(settings.data.days_between_runs); }, [settings.data?.days_between_runs]); // eslint-disable-line react-hooks/exhaustive-deps

  const onStart = () =>
    start.mutate(undefined, {
      onSuccess: () => notifications.show({ message: "הריצה התחילה", color: "teal" }),
      onError: (e) => notifications.show({ message: e instanceof ApiError && e.status === 409 ? "ריצה כבר פועלת" : `שגיאה: ${e.message}`, color: "red" }),
    });
  const onSave = () => {
    const n = Number(days);
    if (!Number.isInteger(n) || n < 1 || n > 60) return notifications.show({ message: "מספר הימים חייב להיות בין 1 ל-60", color: "red" });
    save.mutate(n, { onSuccess: () => notifications.show({ message: "ההגדרות נשמרו", color: "teal" }) });
  };

  return (
    <Stack gap="lg">
      <Title order={2}>ריצות והגדרות</Title>
      <Grid>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card h="100%">
            <Title order={4} mb="md">תזמון</Title>
            <NumberInput label="ריצה מלאה כל" suffix=" ימים" min={1} max={60} value={days} onChange={setDays} w={200} />
            <Group mt="lg">
              <Button onClick={onSave} loading={save.isPending}>שמירה</Button>
              <Button variant="light" leftSection={<IconPlayerPlay size={16} />} disabled={!!running} loading={start.isPending} onClick={onStart}>
                {running ? "ריצה כבר פועלת" : "הרץ כעת"}
              </Button>
            </Group>
            <Text size="sm" mt="lg">ריצה מוצלחת אחרונה: <b>{dateTime(settings.data?.last_run_at)}</b></Text>
            <Text size="sm">ריצה מלאה הבאה: <b>{dateTime(settings.data?.next_run_at)}</b></Text>
            <Text size="xs" c="dimmed" mt={4}>המתזמן בודק כל 15 דקות. אחרי ריצה שנכשלה או נחסמה ממתינים 6 שעות.</Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card h="100%">
            <Title order={4} mb="md">ריצה נוכחית</Title>
            {running ? (
              <Stack gap="xs">
                <Group justify="space-between"><Text>ריצה #{running.id} · התחילה {dateTime(running.started_at)}</Text><Badge color="blue">רצה</Badge></Group>
                <Progress value={running.progress_total ? (running.progress_done / running.progress_total) * 100 : 0} size="lg" animated striped />
                <Text size="sm" c="dimmed">{running.progress_done} מתוך {running.progress_total} דוחות</Text>
              </Stack>
            ) : <Text c="dimmed">אין ריצה פעילה.</Text>}
          </Card>
        </Grid.Col>
      </Grid>

      {runs.error && <Alert color="red">לא הצלחתי לטעון את הריצות.</Alert>}
      <Card p={0}>
        <Title order={4} p="lg" pb="sm">היסטוריה</Title>
        <Table.ScrollContainer minWidth={700}>
          <Table verticalSpacing="sm" horizontalSpacing="lg" highlightOnHover>
            <Table.Thead>
              <Table.Tr><Table.Th>#</Table.Th><Table.Th>הופעלה ע"י</Table.Th><Table.Th>התחילה</Table.Th><Table.Th>הסתיימה</Table.Th><Table.Th>סיכום</Table.Th><Table.Th>סטטוס</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {list.map((r) => (
                <Table.Tr key={r.id} onClick={() => setSelected(r.id)} style={{ cursor: "pointer" }} bg={r.id === logRunId ? "var(--mantine-color-brand-light)" : undefined}>
                  <Table.Td ff="monospace">{r.id}</Table.Td>
                  <Table.Td>{KIND[r.kind] ?? r.kind}</Table.Td>
                  <Table.Td ff="monospace">{dateTime(r.started_at)}</Table.Td>
                  <Table.Td ff="monospace">{dateTime(r.finished_at)}</Table.Td>
                  <Table.Td><Text size="xs" dir="ltr" ta="right">{r.summary ?? r.error ?? ""}</Text></Table.Td>
                  <Table.Td><Badge variant="light" color={STATUS[r.status]?.color ?? "gray"}>{STATUS[r.status]?.label ?? r.status}</Badge></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {logRunId !== null && (
        <Card>
          <Title order={4} mb="sm">לוג — ריצה #{logRunId}</Title>
          <ScrollArea h={280} dir="ltr">
            <Code block>
              {(log.data ?? []).length === 0 ? "(אין שורות לוג)" :
                (log.data ?? []).map((l) => `${l.ts.slice(11, 19)} ${l.level.toUpperCase().padEnd(7)} ${l.message}`).join("\n")}
            </Code>
          </ScrollArea>
        </Card>
      )}
    </Stack>
  );
}
