import { Badge, Box, Group, Stack, Text, Tooltip } from "@mantine/core";
import type { Criterion } from "../api/client";
import { strengthColor } from "../theme";
import { num } from "../format";

const STATUS_TEXT: Record<string, string> = { PASS: "עובר", FAIL: "נכשל", NA: "לא חושב" };

function verdict(c: Criterion): string {
  if (c.status === "NA") return c.result_note ?? "אין נתון";
  if (c.status === "PASS") return (c.strength ?? 0) >= 1 ? "עובר בביטחון" : "עובר, קרוב לסף";
  return (c.strength ?? 0) > 0 ? "נכשל, קרוב לסף" : "נכשל";
}

/** One criterion: title, value, and (for threshold criteria) a bar showing value against the threshold. */
export function CriterionGauge({ c }: { c: Criterion }) {
  const status = c.status as "PASS" | "FAIL" | "NA";
  const color = strengthColor(c.strength ?? 0, status);
  const hasScale = !c.comparative && c.value !== null && c.threshold !== null && (c.direction === ">" || c.direction === "<" || c.direction === ">=" || c.direction === "<=");
  const higherIsBetter = c.direction.startsWith(">");

  let pos = (_v: number) => 0;
  if (hasScale) {
    const lo = Math.min(0, c.value!, c.threshold!);
    let hi = Math.max(c.value!, c.threshold!) * 1.25;
    if (hi <= lo) hi = lo + 1;
    pos = (v: number) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
  }

  return (
    <Stack gap={6} py="sm" style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}>
      <Group justify="space-between" wrap="nowrap" align="flex-start">
        <Tooltip label={c.formula + (c.note ? ` — ${c.note}` : "")} multiline w={340} withArrow events={{ hover: true, focus: true, touch: true }}>
          <Group gap="xs" wrap="nowrap">
            <Text size="xs" c="dimmed" ff="monospace">{c.id}</Text>
            <Text size="sm" dir="ltr">{c.title}</Text>
          </Group>
        </Tooltip>
        <Group gap="xs" wrap="nowrap">
          {c.comparative && c.status !== "NA" ? (
            <Text size="sm" fw={600} ff="monospace" dir="ltr">{num(c.value, 3)} vs {num(c.threshold, 3)}</Text>
          ) : (
            <Text size="sm" fw={600} ff="monospace" dir="ltr">{num(c.value)}</Text>
          )}
          <Badge size="sm" variant="light" color={color}>{STATUS_TEXT[c.status]}</Badge>
        </Group>
      </Group>
      {hasScale && (
        <Box dir="ltr" pos="relative" h={8} style={{ borderRadius: 4, background: "var(--mantine-color-default-hover)" }}>
          <Box
            pos="absolute" top={0} bottom={0}
            style={{
              borderRadius: 4,
              background: "var(--mantine-color-teal-light)",
              ...(higherIsBetter ? { left: `${pos(c.threshold!)}%`, right: 0 } : { left: 0, width: `${pos(c.threshold!)}%` }),
            }}
          />
          <Box pos="absolute" top={-4} bottom={-4} w={2} bg="var(--mantine-color-text)" style={{ left: `${pos(c.threshold!)}%`, opacity: 0.45 }} />
          <Box
            pos="absolute" top={-3} w={14} h={14}
            bg={`var(--mantine-color-${color}-filled)`}
            style={{ left: `calc(${pos(c.value!)}% - 7px)`, borderRadius: "50%", border: "2px solid var(--mantine-color-body)" }}
          />
        </Box>
      )}
      <Group justify="space-between">
        <Text size="xs" c="dimmed">{verdict(c)}</Text>
        {!c.comparative && c.threshold !== null && (
          <Text size="xs" c="dimmed">סף <Text span ff="monospace" dir="ltr">{c.direction} {num(c.threshold)}</Text></Text>
        )}
        {c.comparative && c.status !== "NA" && <Text size="xs" c="dimmed">מול ערך ההשוואה</Text>}
      </Group>
    </Stack>
  );
}
