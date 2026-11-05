"""All configuration, read from environment variables only.

Locally the variables come from `.env` (git-ignored); on Railway from the service Variables.
There is no data folder: the single SQLite file at `DB_PATH` holds everything.
Secrets are excluded from `repr()` so they cannot leak into logs by accident.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DB_PATH = "./var/value_scanner.db"


class SettingsError(RuntimeError):
    """A required setting is missing or invalid. The message names the variable, never its value."""


@dataclass(frozen=True)
class Settings:
    db_path: Path
    # Alert recipient and SEC contact address (D16). Never logged, never committed.
    my_email: str | None = field(default=None, repr=False)
    dashboard_password: str | None = field(default=None, repr=False)
    session_secret: str | None = field(default=None, repr=False)
    google_api_key: str | None = field(default=None, repr=False)

    def require(self, name: str) -> str:
        """Return a secret/optional setting or raise naming the missing env variable."""
        value = getattr(self, name)
        if not value:
            raise SettingsError(f"{name.upper()} is not set")
        return value


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def load_settings(
    env: Mapping[str, str] | None = None, *, load_dotenv_file: bool = False
) -> Settings:
    """Build Settings from `env` (default: `os.environ`).

    `load_dotenv_file=True` first loads `.env` into the process environment (without overriding
    variables that are already set). Tests pass an explicit mapping and leave it False.
    """
    if load_dotenv_file:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    if env is None:
        env = os.environ
    return Settings(
        db_path=Path(_clean(env.get("DB_PATH")) or DEFAULT_DB_PATH).expanduser(),
        my_email=_clean(env.get("MY_EMAIL")),
        dashboard_password=_clean(env.get("DASHBOARD_PASSWORD")),
        session_secret=_clean(env.get("SESSION_SECRET")),
        google_api_key=_clean(env.get("GOOGLE_API_KEY")),
    )
