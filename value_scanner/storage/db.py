"""SQLite connection and schema migrations.

The whole system keeps its data in one SQLite file (`DB_PATH`), in WAL mode so the web app can
read while a run writes. Only `repo.py` should talk to the connection returned here.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def connect(path: str | Path, *, hand_between_threads: bool = False) -> sqlite3.Connection:
    """Open the database (":memory:" for tests), configured for this application.

    `hand_between_threads`: a web request's connection is created in one worker thread and used
    in another (FastAPI runs sync dependencies and endpoints in a thread pool). It is still only
    ever used by one thread at a time, so lifting sqlite3's same-thread check is safe there."""
    memory = str(path) == ":memory:"
    if not memory:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None: we control transactions explicitly (see Repository.transaction).
    conn = sqlite3.connect(
        str(path), isolation_level=None, timeout=30, check_same_thread=not hand_between_threads
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    if not memory:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _migrations() -> list[tuple[int, Path]]:
    found = []
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = _MIGRATION_NAME.match(file.name)
        if not match:
            raise ValueError(f"bad migration file name: {file.name}")
        found.append((int(match.group(1)), file))
    versions = [v for v, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise ValueError(f"migration versions must be 1..N without gaps, got {versions}")
    return found


class SchemaTooNew(RuntimeError):
    """The database was migrated by newer code than this process is running."""


def _load_known() -> list[tuple[int, str]]:
    return [(v, f.read_text(encoding="utf-8")) for v, f in _migrations()]


# Read ONCE, when the process starts. A long-running server must never apply a migration that was
# written to disk after it started: it would run it with its own (older) runner. On 2026-11-06 an
# old `serve` process did exactly that with migration 0002 (a table rebuild that needs foreign keys
# off, which only the newer runner knew) and the cascade wiped every table that references `runs`.
_KNOWN_MIGRATIONS = _load_known()


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
    ).fetchone()
    if row is None:
        return 0
    return conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations in order, each in its own transaction. Returns the new version."""
    current = schema_version(conn)
    if current == 0:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
    newest = _KNOWN_MIGRATIONS[-1][0]
    if current > newest:
        raise SchemaTooNew(
            f"database schema v{current} is newer than this code (v{newest}): restart the server"
        )
    for version, statements in _KNOWN_MIGRATIONS:
        if version <= current:
            continue
        # A table rebuild needs foreign keys off, which cannot be changed inside a transaction.
        fk_off = statements.lstrip().startswith("-- foreign_keys: off")
        if fk_off:
            conn.execute("PRAGMA foreign_keys = OFF")
        try:
            _apply(conn, version, statements, verify_foreign_keys=fk_off)
        finally:
            if fk_off:
                conn.execute("PRAGMA foreign_keys = ON")
    return schema_version(conn)


def _apply(conn: sqlite3.Connection, version: int, statements: str, verify_foreign_keys: bool):
    conn.execute("BEGIN")
    try:
        # executescript would COMMIT first; split on ";" at line ends instead.
        for stmt in _split_statements(statements):
            conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
        if verify_foreign_keys:
            broken = conn.execute("PRAGMA foreign_key_check").fetchall()
            if broken:
                raise RuntimeError(f"migration {version} broke foreign keys: {len(broken)} rows")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _split_statements(script: str) -> list[str]:
    """Split a SQL script into statements (our migrations contain no ';' inside literals)."""
    lines = [line for line in script.splitlines() if not line.strip().startswith("--")]
    cleaned = "\n".join(re.sub(r"\s--.*$", "", line) for line in lines)
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def open_database(path: str | Path) -> sqlite3.Connection:
    """Connect and bring the schema up to date."""
    conn = connect(path)
    migrate(conn)
    return conn
