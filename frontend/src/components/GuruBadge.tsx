import { Badge, Tooltip } from "@mantine/core";
import type { GuruScore } from "../api/client";
import { ratioColor } from "../theme";

export function GuruBadge({ value, label }: { value: GuruScore; label: string }) {
  const color = ratioColor(value.score);
  const na = value.total - value.computed;
  return (
    <Tooltip
      label={`${label}: ${value.passed} מתוך ${value.computed} שחושבו עוברים${na ? ` · ${na} לא חושבו (NA)` : ""}`}
      withArrow
    >
      <Badge variant="light" color={color} size="lg" radius="xl" ff="monospace" miw={52}>
        <span dir="ltr">{value.passed}/{value.computed}</span>
      </Badge>
    </Tooltip>
  );
}
