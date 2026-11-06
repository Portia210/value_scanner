import { Component, type ReactNode } from "react";
import { Alert, Button, Stack, Text } from "@mantine/core";

/** A render error must not blank the whole page: show it, with a way to retry. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error) { console.error("render error", error); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Alert color="red" title="משהו נשבר בתצוגה" m="lg">
        <Stack gap="xs" align="flex-start">
          <Text size="sm">ייתכן שהשרת רץ בגרסה ישנה מהממשק: נסה להפעיל אותו מחדש ולרענן. פרטי השגיאה:</Text>
          <Text size="xs" ff="monospace" dir="ltr">{this.state.error.message}</Text>
          <Button size="xs" variant="light" onClick={() => window.location.reload()}>רענון</Button>
        </Stack>
      </Alert>
    );
  }
}
