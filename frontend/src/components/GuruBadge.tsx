import { Badge, Tooltip } from "@mantine/core";
import type { GuruScore } from "../types";
import { ratioColor } from "../theme";

export function GuruBadge({ value, label }: { value: GuruScore; label: string }) {
  const color = ratioColor(value.score);
  return (
    <Tooltip label={`${label}: ${value.passed} מתוך ${value.total} קריטריונים עוברים`} withArrow>
      <Badge variant="light" color={color} size="lg" radius="xl" ff="monospace" miw={52}>
        <span dir="ltr">{value.passed}/{value.total}</span>
      </Badge>
    </Tooltip>
  );
}
