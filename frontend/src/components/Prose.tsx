import { Anchor, Divider, List, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

/** Inline **bold** only; the profile text is generated Markdown with a tiny, fixed vocabulary. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <b key={i}>{part.slice(2, -2)}</b> : part,
  );
}

/** Minimal Markdown: `##`/`###` headings, `---`, `*`/`-` bullets (nesting by indent), paragraphs. */
export function Prose({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let bullets: { depth: number; text: string }[] = [];
  const flush = () => {
    if (!bullets.length) return;
    const items = bullets;
    bullets = [];
    blocks.push(
      <List key={`l${blocks.length}`} size="sm" spacing={4}>
        {items.map((b, i) => (
          <List.Item key={i} ml={b.depth * 18}>{inline(b.text)}</List.Item>
        ))}
      </List>,
    );
  };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const bullet = /^(\s*)[*-]\s+(.*)$/.exec(line);
    if (bullet) { bullets.push({ depth: Math.floor(bullet[1].length / 2), text: bullet[2] }); continue; }
    flush();
    if (!line.trim()) continue;
    if (/^-{3,}$/.test(line.trim())) blocks.push(<Divider key={blocks.length} />);
    else if (line.startsWith("### ")) blocks.push(<Title key={blocks.length} order={6}>{inline(line.slice(4))}</Title>);
    else if (line.startsWith("## ")) blocks.push(<Title key={blocks.length} order={5} mt="xs">{inline(line.slice(3))}</Title>);
    else blocks.push(<Text key={blocks.length} size="sm">{inline(line)}</Text>);
  }
  flush();
  return <Stack gap="xs">{blocks}</Stack>;
}

export const SourceLink = ({ href }: { href: string }) => (
  <Anchor href={href} target="_blank" rel="noopener noreferrer" size="xs">לדוח המקור ב-SEC</Anchor>
);
