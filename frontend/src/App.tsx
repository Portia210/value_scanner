import { ActionIcon, Alert, AppShell, Burger, Button, Container, Drawer, Group, Loader, Stack, Text, Center, useMantineColorScheme } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconHistory, IconLayoutDashboard, IconLogout, IconMath, IconMoon, IconPlayerPlay, IconScale, IconSun, IconTransfer } from "@tabler/icons-react";
import { NavLink, Route, Routes } from "react-router-dom";
import { notifications } from "@mantine/notifications";
import { ApiError } from "./api/client";
import { useHealth, useRuns, useSettings, useStartRun } from "./api/hooks";
import { EXPECTED_API_VERSION } from "./api/version";
import { useAuth } from "./auth";
import { dateTime } from "./format";
import { CriteriaPage } from "./pages/CriteriaPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { RunsPage } from "./pages/RunsPage";
import { StockPage } from "./pages/StockPage";

const NAV = [
  { to: "/", label: "דשבורד", icon: IconLayoutDashboard },
  { to: "/history", label: "כניסות ויציאות", icon: IconTransfer },
  { to: "/runs", label: "ריצות", icon: IconHistory },
  { to: "/criteria", label: "איך זה מחושב", icon: IconMath },
];

function RunNow() {
  const runs = useRuns();
  const start = useStartRun();
  const running = runs.data?.some((r) => r.status === "running");
  return (
    <Button size="xs" leftSection={<IconPlayerPlay size={14} />} disabled={!!running} loading={start.isPending}
      onClick={() => start.mutate(undefined, {
        onSuccess: () => notifications.show({ message: "הריצה התחילה", color: "teal" }),
        onError: (e) => notifications.show({ message: e instanceof ApiError && e.status === 409 ? "ריצה כבר פועלת" : `שגיאה: ${e.message}`, color: "red" }),
      })}>
      {running ? "ריצה פועלת…" : "הרץ כעת"}
    </Button>
  );
}

function NavButtons({ onNavigate }: { onNavigate?: () => void }) {
  return NAV.map(({ to, label, icon: Icon }) => (
    <Button key={to} component={NavLink} to={to} end={to === "/"} variant="subtle" color="gray" size="sm" onClick={onNavigate}
      leftSection={<Icon size={16} />}
      style={({ isActive }: { isActive: boolean }) => (isActive ? { color: "var(--mantine-color-brand-6)", background: "var(--mantine-color-brand-light)" } : undefined)}>
      {label}
    </Button>
  ));
}

export function App() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const { loggedIn, loading, logout } = useAuth();
  const [drawer, { toggle, close }] = useDisclosure(false);
  const settings = useSettings();
  const health = useHealth();
  const staleServer = health.isSuccess && health.data.api_version !== EXPECTED_API_VERSION;

  if (loading) return <Center h="100vh"><Loader /></Center>;
  if (!loggedIn) return <LoginPage />;

  return (
    <AppShell header={{ height: 60 }} padding="lg">
      <AppShell.Header>
        <Container size="xl" h="100%">
          <Group h="100%" justify="space-between" wrap="nowrap">
            <Group gap="xs" wrap="nowrap">
              <Burger opened={drawer} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="תפריט" />
              <IconScale size={24} color="var(--mantine-color-brand-6)" />
              <Text fw={700} size="lg">סורק ערך</Text>
            </Group>
            <Group gap={4} visibleFrom="sm"><NavButtons /></Group>
            <Group gap="xs" wrap="nowrap">
              <Text size="xs" c="dimmed" visibleFrom="lg">
                עודכן {dateTime(settings.data?.last_run_at)} · הבאה {dateTime(settings.data?.next_run_at)}
              </Text>
              <RunNow />
              <ActionIcon variant="subtle" color="gray" onClick={toggleColorScheme} aria-label="החלפת מצב תצוגה">
                {colorScheme === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
              </ActionIcon>
              <ActionIcon variant="subtle" color="gray" onClick={() => void logout()} aria-label="יציאה">
                <IconLogout size={18} />
              </ActionIcon>
            </Group>
          </Group>
        </Container>
      </AppShell.Header>
      <Drawer opened={drawer} onClose={close} size="xs" title="תפריט"><Stack><NavButtons onNavigate={close} /></Stack></Drawer>
      <AppShell.Main>
        <Container size="xl">
          {staleServer && (
            <Alert color="red" variant="filled" mb="md" title="השרת רץ בגרסה ישנה מהממשק">
              חלק מהפעולות לא יעבדו (ניתוח לפי טיקר, תיאור חברה, מניות שיצאו מהמעקב). עצור את serve והפעל אותו מחדש, ואז רענן.
            </Alert>
          )}
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/stocks/:symbol" element={<StockPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/criteria" element={<CriteriaPage />} />
            <Route path="*" element={<Text c="dimmed">העמוד לא נמצא.</Text>} />
          </Routes>
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
