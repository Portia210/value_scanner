import { createTheme, type MantineColorsTuple } from "@mantine/core";

const brand: MantineColorsTuple = [
  "#e8f3ff", "#d2e3fb", "#a3c4f3", "#71a3ec", "#4888e6", "#2f76e3", "#1f6de2", "#0f5cc9", "#0051b5", "#0046a1",
];

export const theme = createTheme({
  primaryColor: "brand",
  colors: { brand },
  fontFamily: "Heebo, system-ui, sans-serif",
  fontFamilyMonospace: "'JetBrains Mono', ui-monospace, monospace",
  headings: { fontFamily: "Heebo, system-ui, sans-serif", fontWeight: "600" },
  defaultRadius: "md",
  cursorType: "pointer",
  components: {
    Card: { defaultProps: { withBorder: true, radius: "lg", padding: "lg" } },
  },
});

// Semantic colours for criteria results — one meaning each, used everywhere.
export const STATUS_COLORS = {
  strong: "teal", // passes with ≥20% margin
  near: "yellow", // passes, but within 20% of the threshold
  weak: "orange", // fails by less than 20%
  fail: "red",
  na: "gray",
} as const;

export function strengthColor(strength: number, status: "PASS" | "FAIL" | "NA" | "MANUAL"): string {
  if (status === "NA" || status === "MANUAL") return STATUS_COLORS.na;
  if (strength >= 1) return STATUS_COLORS.strong;
  if (strength >= 0.75) return STATUS_COLORS.near;
  if (strength > 0) return STATUS_COLORS.weak;
  return STATUS_COLORS.fail;
}

export function ratioColor(score: number | null): string {
  if (score === null) return STATUS_COLORS.na;
  if (score >= 0.8) return STATUS_COLORS.strong;
  if (score >= 0.55) return STATUS_COLORS.near;
  return STATUS_COLORS.fail;
}
