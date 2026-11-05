import { Badge, Box, Group, Stack, Text } from "@mantine/core";
import type { CriterionResult } from "../types";
import { strengthColor } from "../theme";
import { dirOf } from "../format";

const STATUS_TEXT: Record<CriterionResult["status"], string> = { PASS: "עובר", FAIL: "נכשל", NA: "לא רלוונטי" };

function verdict(c: CriterionResult): string {
  if (c.status === "NA") return c.note ?? "לא חושב";
  if (c.status === "PASS") return c.strength >= 1 ? "עובר בביטחון" : "עובר, קרוב לסף";
  return c.strength > 0 ? "נכשל, קרוב לסף" : "נכשל";
}

/** One criterion: title, value, and (for threshold criteria) a bar showing value vs threshold. */
export function CriterionGauge({ c }: { c: CriterionResult }) {
  const color = strengthColor(c.strength, c.status);
  const hasScale = c.value !== undefined && c.threshold !== undefined && c.scaleMax && (c.op === ">" || c.op === "<");
  const pos = (v: number) => Math.max(0, Math.min(100, (v / (c.scaleMax ?? 1)) * 100));

  return (
    <Stack gap={6} py="sm" style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}>
      <Group justify="space-between" wrap="nowrap">
        <Group gap="xs" wrap="nowrap">
          <Text size="xs" c="dimmed" ff="monospace">{c.id}</Text>
          <Text size="sm">{c.title}</Text>
        </Group>
        <Group gap="xs" wrap="nowrap">
          <Text size="sm" fw={600} ff="monospace" dir={dirOf(c.display)}>{c.display}</Text>
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
              ...(c.op === ">" ? { left: `${pos(c.threshold!)}%`, right: 0 } : { left: 0, width: `${pos(c.threshold!)}%` }),
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
        {hasScale && <Text size="xs" c="dimmed">סף <Text span ff="monospace" dir="ltr">{c.threshold}</Text></Text>}
      </Group>
    </Stack>
  );
}
