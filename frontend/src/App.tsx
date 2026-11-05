import { ActionIcon, Alert, AppShell, Button, Container, Group, Text, useMantineColorScheme } from "@mantine/core";
import { IconChartDots3, IconHistory, IconLayoutDashboard, IconMath, IconMoon, IconPlayerPlay, IconScale, IconSun } from "@tabler/icons-react";
import { NavLink, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { RunsPage } from "./pages/RunsPage";
import { StockPage } from "./pages/StockPage";

const NAV = [
  { to: "/", label: "דשבורד", icon: IconLayoutDashboard },
  { to: "/stocks/CSW", label: "דף מניה", icon: IconChartDots3 },
  { to: "/runs", label: "ריצות", icon: IconHistory },
  { to: "/criteria", label: "איך זה מחושב", icon: IconMath },
];

export function App() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  return (
    <AppShell header={{ height: 60 }} padding="lg">
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Group h="100%" justify="space-between" wrap="nowrap">
            <Group gap="xs" wrap="nowrap">
              <IconScale size={24} color="var(--mantine-color-brand-6)" />
              <Text fw={700} size="lg">סורק ערך</Text>
            </Group>
            <Group gap={4} visibleFrom="sm">
              {NAV.map(({ to, label, icon: Icon }) => (
                <Button key={to} component={NavLink} to={to} end variant="subtle" color="gray" size="sm"
                  leftSection={<Icon size={16} />}
                  style={({ isActive }: { isActive: boolean }) => (isActive ? { color: "var(--mantine-color-brand-6)", background: "var(--mantine-color-brand-light)" } : undefined)}>
                  {label}
                </Button>
              ))}
            </Group>
            <Group gap="xs" wrap="nowrap">
              <Text size="xs" c="dimmed" visibleFrom="md">עודכן לפני יומיים · הבאה בעוד 3 ימים</Text>
              <Button size="xs" leftSection={<IconPlayerPlay size={14} />}>הרץ כעת</Button>
              <ActionIcon variant="subtle" color="gray" onClick={toggleColorScheme} aria-label="החלפת מצב תצוגה">
                {colorScheme === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
              </ActionIcon>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="xl">
          <Alert color="yellow" variant="light" mb="lg" py={6}>
            <Text size="sm">דוגמת עיצוב — כל המספרים בדף הם נתוני דמה.</Text>
          </Alert>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/stocks/:symbol" element={<StockPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="*" element={<Text c="dimmed">העמוד הזה ייבנה בהמשך.</Text>} />
          </Routes>
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
