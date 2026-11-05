import { useState } from "react";
import { Alert, Button, Card, Center, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { ApiError } from "../api/client";
import { useAuth } from "../auth";

export function LoginPage() {
  const { login } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await login(password);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 429 ? "יותר מדי ניסיונות. נסה שוב בעוד כמה דקות." : "הסיסמה שגויה.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Center h="100vh">
      <Card w={340} shadow="sm">
        <form onSubmit={(e) => { e.preventDefault(); void submit(); }}>
          <Stack>
            <Title order={3}>סורק ערך</Title>
            <Text size="sm" c="dimmed">הכנס את סיסמת הדשבורד.</Text>
            <PasswordInput label="סיסמה" value={password} onChange={(e) => setPassword(e.currentTarget.value)} autoFocus required />
            {error && <Alert color="red" py={6}>{error}</Alert>}
            <Button type="submit" loading={busy}>כניסה</Button>
          </Stack>
        </form>
      </Card>
    </Center>
  );
}
