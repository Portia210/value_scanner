import { useState } from "react";
import { Alert, Anchor, Button, Card, Group, Loader, Stack, Switch, Table, Tabs, Text, TextInput, Title } from "@mantine/core";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useLearn } from "../api/hooks";
import type { components } from "../api/schema";
import { updated } from "../format";

type Row = components["schemas"]["LearnRow"];
type Statement = components["schemas"]["LearnStatement"];

const EXPLAIN_KEY = "learn-explain";

function fmt(v: number | null, kind: string): string {
  if (v === null) return "—";
  if (kind === "pct") return `${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}%`;
  return v.toLocaleString("en-US", { maximumFractionDigits: Math.abs(v) >= 1000 ? 0 : 2 });
}

/** "TTM" -> "12 חודשים אחרונים"; "FY 2025" -> "2025". */
function periodLabel(p: string): string {
  if (p === "TTM") return "12 חודשים אחרונים";
  return p.replace(/^FY\s*/, "");
}

function LineRow({ row, periods, explain, open, onToggle }: { row: Row; periods: string[]; explain: boolean; open: boolean; onToggle: () => void }) {
  const total = row.kind === "total";
  const pct = row.kind === "pct";
  const detail = !!(row.how || row.look);
  return (
    <>
      <Table.Tr onClick={detail ? onToggle : undefined} style={{ cursor: detail ? "pointer" : undefined, background: open ? "var(--mantine-color-brand-light)" : undefined }}>
        <Table.Td style={{ verticalAlign: "top", minWidth: 220, paddingInlineStart: pct ? 24 : undefined }}>
          <Text size="sm" fw={total ? 700 : 400} fs={pct ? "italic" : undefined} c={pct ? "dimmed" : undefined}>
            {row.he ?? row.item}{" "}
            {row.he && <Text span size="xs" c="dimmed" dir="ltr" fw={400} fs="normal">{row.item}</Text>}
          </Text>
          {explain && row.short && <Text size="xs" c="dimmed" mt={2}>{row.short}</Text>}
        </Table.Td>
        {row.values.map((v, i) => (
          <Table.Td key={periods[i]} ta="left" style={{ verticalAlign: "top", whiteSpace: "nowrap" }}>
            <Text size="sm" ff="monospace" fw={total ? 700 : 400} fs={pct ? "italic" : undefined} c={pct ? "dimmed" : undefined} dir="ltr">{fmt(v, row.kind)}</Text>
          </Table.Td>
        ))}
      </Table.Tr>
      {open && detail && (
        <Table.Tr style={{ background: "var(--mantine-color-brand-light)" }}>
          <Table.Td colSpan={periods.length + 1}>
            <Stack gap={4}>
              {row.how && <Text size="sm"><Text span c="dimmed">איך זה מחושב: </Text><bdi>{row.how}</bdi></Text>}
              {row.look && <Text size="sm"><Text span c="dimmed">על מה להסתכל: </Text>{row.look}</Text>}
            </Stack>
          </Table.Td>
        </Table.Tr>
      )}
    </>
  );
}

function StatementTable({ st, explain }: { st: Statement; explain: boolean }) {
  const [openItem, setOpenItem] = useState<string | null>(null);
  return (
    <Table.ScrollContainer minWidth={760}>
      <Table verticalSpacing={6} horizontalSpacing="md">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>סעיף</Table.Th>
            {st.periods.map((p) => <Table.Th key={p} ta="left">{periodLabel(p)}</Table.Th>)}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {st.rows.map((r) => (
            <LineRow key={r.item} row={r} periods={st.periods} explain={explain}
              open={openItem === r.item} onToggle={() => setOpenItem(openItem === r.item ? null : r.item)} />
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

/** Learning page: every line of a company's statements as on StockAnalysis, with its meaning under it. */
export function LearnPage() {
  const { symbol = "" } = useParams();
  const sym = symbol.toUpperCase();
  const navigate = useNavigate();
  const [input, setInput] = useState(sym);
  const [explain, setExplain] = useState(() => {
    try { return localStorage.getItem(EXPLAIN_KEY) !== "0"; } catch { return true; }
  });
  const { data, isLoading, error } = useLearn(sym);
  const toggle = (on: boolean) => {
    setExplain(on);
    try { localStorage.setItem(EXPLAIN_KEY, on ? "1" : "0"); } catch { /* private mode */ }
  };
  const go = () => { const s = input.trim().toUpperCase(); if (s) navigate(`/learn/${s}`); };

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>למידה: קריאת דוחות כספיים</Title>
        <Text c="dimmed" size="sm">כל שורה בדוחות של חברה, עם הסבר מתחתיה. לחיצה על שורה פותחת עוד פירוט.</Text>
      </div>
      <Group align="end" gap="xs">
        <TextInput label="סימול מניה" placeholder="TSM" value={input} dir="ltr" w={160}
          onChange={(e) => setInput(e.currentTarget.value)} onKeyDown={(e) => e.key === "Enter" && go()} />
        <Button onClick={go}>הצג</Button>
      </Group>

      {sym === "" && <Text c="dimmed">הכנס סימול של מניה שכבר נותחה באתר, למשל TSM.</Text>}
      {sym !== "" && isLoading && <Loader />}
      {error instanceof ApiError && error.status === 404 && (
        <Alert color="gray">
          עוד אין דוחות שמורים של {sym}. אפשר להוריד אותם בעמוד המניה: <Anchor component={Link} to={`/stocks/${sym}`}>נתח את {sym}</Anchor>.
        </Alert>
      )}
      {error && !(error instanceof ApiError && error.status === 404) && <Alert color="red">לא הצלחתי לטעון את הדוחות.</Alert>}

      {data && (
        <Card>
          <Group justify="space-between" mb="sm" align="start">
            <div>
              <Group gap="xs">
                <Title order={3} ff="monospace">{data.symbol}</Title>
                <Text c="dimmed" dir="ltr">{data.name}</Text>
              </Group>
              <Text size="xs" c="dimmed">{updated(data.statements[0]?.fetched_at)} · 5 שנות כספים ו-12 החודשים האחרונים</Text>
              {data.statements[0]?.currency ? (
                <Text size="sm" fw={600} c="orange" mt={6}>מטבע הדיווח: {data.statements[0].currency}. הסכומים במיליונים.</Text>
              ) : (
                <Text size="xs" c="dimmed" mt={6}>הסכומים במטבע הדיווח של החברה, שאינו תמיד דולר. המטבע יוצג אחרי ההורדה הבאה של הדוחות.</Text>
              )}
            </div>
            <Switch size="xs" label="הסברים מתחת לכל שורה" checked={explain} onChange={(e) => toggle(e.currentTarget.checked)} />
          </Group>
          <Tabs defaultValue={data.statements[0]?.key}>
            <Tabs.List>{data.statements.map((s) => <Tabs.Tab key={s.key} value={s.key}>{s.label}</Tabs.Tab>)}</Tabs.List>
            {data.statements.map((s) => (
              <Tabs.Panel key={s.key} value={s.key} pt="sm"><StatementTable st={s} explain={explain} /></Tabs.Panel>
            ))}
          </Tabs>
        </Card>
      )}
    </Stack>
  );
}
