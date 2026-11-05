"""Login, signed session cookie, CSRF token and login rate limiting (plan section 2a)."""

from __future__ import annotations

import hmac
import secrets
import time
from collections import defaultdict, deque

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "vs_session"
SESSION_MAX_AGE = 7 * 24 * 3600
MAX_FAILED_LOGINS = 5
LOGIN_WINDOW = 15 * 60

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
}


LOCAL_CSRF = "local-mode"  # no session in local mode; the header is still required
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def is_local_host(host_header: str) -> bool:
    """True for a Host header naming this machine (port allowed). Blocks DNS rebinding."""
    host = host_header.strip().lower()
    if host.startswith("["):
        host = host.split("]")[0] + "]"
    else:
        host = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    return host in LOCAL_HOSTS


def is_loopback_bind(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def password_matches(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode(), expected.encode())


class SessionSigner:
    def __init__(self, secret: str):
        self._serializer = URLSafeTimedSerializer(secret, salt="value-scanner-session")

    def issue(self) -> tuple[str, str]:
        """Returns (cookie value, csrf token)."""
        csrf = secrets.token_urlsafe(24)
        return self._serializer.dumps({"csrf": csrf}), csrf

    def read(self, cookie: str | None) -> str | None:
        """The CSRF token of a valid session, else None."""
        if not cookie:
            return None
        try:
            data = self._serializer.loads(cookie, max_age=SESSION_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        return data.get("csrf") if isinstance(data, dict) else None


class LoginLimiter:
    """At most MAX_FAILED_LOGINS failures per client in LOGIN_WINDOW seconds."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        q = self._failures[key]
        while q and self._clock() - q[0] > LOGIN_WINDOW:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= MAX_FAILED_LOGINS

    def fail(self, key: str) -> None:
        self._prune(key).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
