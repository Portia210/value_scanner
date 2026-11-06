import { Stack, Text } from "@mantine/core";
import { FILTER_LABELS, num } from "../format";

type Change = { before: number | null; after: number | null };

/**
 * What changed in a membership event: one line per screener filter, "label: before → after".
 * The label is Hebrew (right-to-left); the numbers are isolated as left-to-right so that
 * "2.00B → 1.99B" is not scrambled by the bidi algorithm.
 */
export function FilterChanges({ detail }: { detail: unknown }) {
  const rows = Object.entries((detail ?? {}) as Record<string, Change>).filter(
    ([, v]) => v && typeof v === "object" && "after" in v,
  );
  if (rows.length === 0) return <Text size="sm" c="dimmed">—</Text>;
  return (
    <Stack gap={2}>
      {rows.map(([k, v]) => (
        <Text size="sm" key={k}>
          {FILTER_LABELS[k] ?? k}:{" "}
          <bdi dir="ltr">
            {num(v.before)} → {num(v.after)}
          </bdi>
        </Text>
      ))}
    </Stack>
  );
}
