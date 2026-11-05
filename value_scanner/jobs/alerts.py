"""Send stored alerts by email to MY_EMAIL (B4).

Alerts are always written to the `alerts` table first; sending is best-effort and a failure to
send never fails a run. Subjects and bodies must not contain secrets or the recipient address.
"""

from __future__ import annotations

import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage

from value_scanner.settings import Settings
from value_scanner.storage.repo import Repository

Sender = Callable[[EmailMessage], None]


def smtp_sender(settings: Settings) -> Sender:
    """A sender that delivers through the configured SMTP server."""

    def send(message: EmailMessage) -> None:
        host = settings.require("smtp_host")
        context = ssl.create_default_context()
        if settings.smtp_port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                host, settings.smtp_port, context=context, timeout=30
            )
        else:
            server = smtplib.SMTP(host, settings.smtp_port, timeout=30)
        with server:
            if settings.smtp_port != 465:
                server.starttls(context=context)
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)

    return send


def build_message(settings: Settings, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["To"] = settings.require("my_email")
    message["From"] = settings.smtp_from or settings.require("smtp_user")
    message["Subject"] = f"[value-scanner] {subject}"
    message.set_content(body)
    return message


def send_pending_alerts(
    repo: Repository, settings: Settings, sender: Sender | None = None
) -> tuple[int, int]:
    """Try to send every unsent alert. Returns (sent, failed). Failures are recorded on the row
    and retried on the next call."""
    rows = repo.conn.execute(
        "SELECT id, subject, body FROM alerts WHERE sent_at IS NULL ORDER BY id"
    ).fetchall()
    if not rows:
        return 0, 0
    if sender is None:
        if not (settings.smtp_host and settings.my_email):
            for row in rows:
                repo.mark_alert_sent(row["id"], error="email not configured (SMTP_HOST, MY_EMAIL)")
            return 0, len(rows)
        sender = smtp_sender(settings)
    sent = failed = 0
    for row in rows:
        try:
            sender(build_message(settings, row["subject"], row["body"]))
        except Exception as exc:  # noqa: BLE001 - any delivery error is recorded, not raised
            repo.mark_alert_sent(row["id"], error=f"{type(exc).__name__}: {exc}"[:300])
            failed += 1
        else:
            repo.mark_alert_sent(row["id"])
            sent += 1
    return sent, failed


def send_test_alert(settings: Settings, sender: Sender | None = None) -> None:
    """Send one harmless message to MY_EMAIL through the configured SMTP (nothing is stored).
    Raises if email is not configured or delivery fails."""
    if not (settings.smtp_host and settings.my_email):
        raise RuntimeError("email not configured (SMTP_HOST, MY_EMAIL)")
    sender = sender or smtp_sender(settings)
    sender(
        build_message(
            settings,
            "test alert",
            "This is a test message from `python -m value_scanner test-alert`. "
            "If you can read it, run alerts (blocked, structure change, failures) will reach you.",
        )
    )
