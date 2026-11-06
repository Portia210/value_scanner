import { useState } from "react";
import { Alert, Badge, Box, Card, Group, Loader, SegmentedControl, Stack, Table, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useHistory } from "../api/hooks";
import { FilterChanges } from "../components/FilterChanges";
import { dateTime, REASON_LABELS } from "../format";

/** E6: when a stock entered or left the initial screen, and why. */
export function HistoryPage() {
  const { data, isLoading, error } = useHistory();
  const [reason, setReason] = useState("all");
  if (isLoading) return <Loader />;
  if (error || !data) return <Alert color="red">לא הצלחתי לטעון את ההיסטוריה.</Alert>;
  const events = data.events.filter((e) => reason === "all" || e.reason_type === reason);

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>היסטוריית כניסות ויציאות</Title>
          <Text c="dimmed" size="sm">מניה שנכנסה או יצאה מהסינון הראשוני, והסיבה: שינוי מחיר (שווי שוק, P/E) או דוחות חדשים.</Text>
        </div>
        <Box maw="100%" style={{ overflowX: "auto" }}>
        <SegmentedControl value={reason} onChange={setReason}
          data={[{ value: "all", label: "הכול" }, ...Object.entries(REASON_LABELS).map(([value, label]) => ({ value, label }))]} />
        </Box>
      </Group>
      <Card p={0}>
        {events.length === 0 ? (
          <Text c="dimmed" p="lg">אין אירועים. אירועים נרשמים מהריצה השנייה ואילך, כשיש עם מה להשוות.</Text>
        ) : (
          <Table.ScrollContainer minWidth={720}>
            <Table verticalSpacing="sm" horizontalSpacing="lg" highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>מתי</Table.Th><Table.Th>מניה</Table.Th><Table.Th>אירוע</Table.Th><Table.Th>סיבה</Table.Th><Table.Th>פירוט</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {events.map((e) => (
                  <Table.Tr key={e.id}>
                    <Table.Td ff="monospace">{dateTime(e.created_at)}</Table.Td>
                    <Table.Td>
                      <Text component={Link} to={`/stocks/${e.symbol}`} fw={600} ff="monospace" c="brand">{e.symbol}</Text>
                      <Text size="xs" c="dimmed" dir="ltr" ta="right">{e.name}</Text>
                    </Table.Td>
                    <Table.Td><Badge variant="light" color={e.direction === "enter" ? "teal" : "red"}>{e.direction === "enter" ? "נכנסה" : "יצאה"}</Badge></Table.Td>
                    <Table.Td>{REASON_LABELS[e.reason_type] ?? e.reason_type}</Table.Td>
                    <Table.Td><FilterChanges detail={e.detail} /></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>
    </Stack>
  );
}
