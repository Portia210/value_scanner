"""The only module that talks to the database.

Plain SQL (portable to Postgres), no ORM. Every method takes/returns plain Python values or
`sqlite3.Row`. Time comes from an injectable clock so tests and retention are deterministic.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

# Retention policy (plans/v2-rebuild.md section 2).
RUN_LOG_DAYS = 90
SNAPSHOT_DAYS = 400
STATEMENT_FETCHES_KEPT = 4
FAILED_FETCH_DAYS = 90

ISO = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime(ISO)


class RunAlreadyRunning(RuntimeError):
    """Another run holds the lock."""


class Repository:
    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], datetime] = utc_now):
        self.conn = conn
        self._clock = clock

    def now(self) -> str:
        return iso(self._clock())

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Atomic block (the connection is in autocommit mode). Not re-entrant."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        self.conn.execute("COMMIT")

    # ── settings ────────────────────────────────────────────────────────────────────────────
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (key) DO UPDATE SET "
            "value = excluded.value, updated_at = excluded.updated_at",
            (key, value, self.now()),
        )

    # ── runs ────────────────────────────────────────────────────────────────────────────────
    def start_run(self, kind: str) -> int:
        """Create a 'running' run; the unique index is the lock. Raises RunAlreadyRunning."""
        try:
            cur = self.conn.execute(
                "INSERT INTO runs (kind, status, started_at) VALUES (?, 'running', ?)",
                (kind, self.now()),
            )
        except sqlite3.IntegrityError as exc:
            if "runs.status" in str(exc) or "UNIQUE" in str(exc):
                raise RunAlreadyRunning("a run is already in progress") from exc
            raise
        return int(cur.lastrowid)

    def update_progress(self, run_id: int, done: int, total: int) -> None:
        self.conn.execute(
            "UPDATE runs SET progress_done = ?, progress_total = ? WHERE id = ?",
            (done, total, run_id),
        )

    def finish_run(
        self, run_id: int, status: str, summary: str | None = None, error: str | None = None
    ) -> None:
        if status == "running":
            raise ValueError("finish_run needs a final status")
        self.conn.execute(
            "UPDATE runs SET status = ?, finished_at = ?, summary = ?, error = ? WHERE id = ?",
            (status, self.now(), summary, error, run_id),
        )

    def mark_interrupted_runs(self) -> int:
        """At startup: a 'running' row left by a crashed process becomes 'interrupted'."""
        cur = self.conn.execute(
            "UPDATE runs SET status = 'interrupted', finished_at = ? WHERE status = 'running'",
            (self.now(),),
        )
        return cur.rowcount

    def get_run(self, run_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()

    def last_successful_run(self) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM runs WHERE status = 'ok' AND kind <> 'adhoc' "
            "ORDER BY started_at DESC, id DESC LIMIT 1"
        ).fetchone()

    def log(self, run_id: int, level: str, message: str) -> None:
        self.conn.execute(
            "INSERT INTO run_log (run_id, ts, level, message) VALUES (?, ?, ?, ?)",
            (run_id, self.now(), level, message),
        )

    def run_log(self, run_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM run_log WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()

    # ── alerts and parse failures ───────────────────────────────────────────────────────────
    def add_alert(self, kind: str, subject: str, body: str, run_id: int | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO alerts (run_id, kind, subject, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, kind, subject, body, self.now()),
        )
        return int(cur.lastrowid)

    def mark_alert_sent(self, alert_id: int, error: str | None = None) -> None:
        self.conn.execute(
            "UPDATE alerts SET sent_at = ?, error = ? WHERE id = ?",
            (None if error else self.now(), error, alert_id),
        )

    def add_parse_failure(
        self,
        source: str,
        kind: str,
        sample: str,
        symbol: str | None = None,
        run_id: int | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO parse_failures (run_id, symbol, source, kind, sample, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, symbol, source, kind, sample[:2000], self.now()),
        )

    # ── companies ───────────────────────────────────────────────────────────────────────────
    def upsert_company(
        self,
        symbol: str,
        *,
        name: str | None = None,
        country: str | None = None,
        exchange: str | None = None,
        sector: str | None = None,
        industry: str | None = None,
        sic_description: str | None = None,
        cik: str | None = None,
    ) -> None:
        """Insert or update; a None argument keeps the stored value."""
        now = self.now()
        self.conn.execute(
            """INSERT INTO companies (symbol, name, country, exchange, sector, industry,
                                      sic_description, cik, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (symbol) DO UPDATE SET
                   name = COALESCE(excluded.name, name),
                   country = COALESCE(excluded.country, country),
                   exchange = COALESCE(excluded.exchange, exchange),
                   sector = COALESCE(excluded.sector, sector),
                   industry = COALESCE(excluded.industry, industry),
                   sic_description = COALESCE(excluded.sic_description, sic_description),
                   cik = COALESCE(excluded.cik, cik),
                   last_seen_at = excluded.last_seen_at""",
            (symbol, name, country, exchange, sector, industry, sic_description, cik, now, now),
        )

    def get_company(self, symbol: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM companies WHERE symbol = ?", (symbol,)).fetchone()

    # ── screener snapshots and membership ───────────────────────────────────────────────────
    SNAPSHOT_COLUMNS = (
        "in_screen",
        "filters_failed",
        "price",
        "price_date",
        "market_cap",
        "pe_ratio",
        "ps_ratio",
        "pb_ratio",
        "pocf_ratio",
        "pe_ratio_5y",
        "last_earnings_date",
        "next_earnings_date",
        "revenue_growth_5y",
        "profit_margin",
        "eps_growth_5y",
        "debt_equity",
        "current_ratio",
        "roe_5y",
    )

    def save_snapshot(self, run_id: int, symbol: str, values: Mapping[str, Any]) -> None:
        unknown = set(values) - set(self.SNAPSHOT_COLUMNS)
        if unknown:
            raise ValueError(f"unknown snapshot fields: {sorted(unknown)}")
        columns = ["run_id", "symbol", "captured_at", *values]
        params = [run_id, symbol, self.now(), *values.values()]
        marks = ", ".join("?" for _ in columns)
        self.conn.execute(
            f"INSERT INTO screener_snapshots ({', '.join(columns)}) VALUES ({marks})", params
        )

    def snapshots_for_run(self, run_id: int) -> dict[str, sqlite3.Row]:
        rows = self.conn.execute(
            "SELECT * FROM screener_snapshots WHERE run_id = ?", (run_id,)
        ).fetchall()
        return {r["symbol"]: r for r in rows}

    def add_membership_event(
        self,
        run_id: int,
        symbol: str,
        direction: str,
        reason_type: str,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO membership_events (run_id, symbol, direction, reason_type, detail, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                symbol,
                direction,
                reason_type,
                json.dumps(detail, sort_keys=True) if detail is not None else None,
                self.now(),
            ),
        )

    def membership_events(self, symbol: str | None = None) -> list[sqlite3.Row]:
        if symbol is None:
            return self.conn.execute(
                "SELECT * FROM membership_events ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM membership_events WHERE symbol = ? ORDER BY created_at DESC, id DESC",
            (symbol,),
        ).fetchall()

    # ── financial statements ────────────────────────────────────────────────────────────────
    def save_statement_fetch(
        self,
        symbol: str,
        statement: str,
        source: str,
        status: str,
        values: Iterable[tuple[str, str, float | None]] = (),
        latest_period: str | None = None,
        run_id: int | None = None,
    ) -> int:
        """Record one download and its (item, period, value) rows; keep the 4 latest good ones."""
        with self.transaction():
            cur = self.conn.execute(
                "INSERT INTO statement_fetches (run_id, symbol, statement, fetched_at, source, "
                "status, latest_period) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, symbol, statement, self.now(), source, status, latest_period),
            )
            fetch_id = int(cur.lastrowid)
            self.conn.executemany(
                "INSERT INTO statement_values (fetch_id, item, period, value) VALUES (?, ?, ?, ?)",
                [(fetch_id, item, period, value) for item, period, value in values],
            )
            self._prune_statement_fetches(symbol, statement)
        return fetch_id

    def _prune_statement_fetches(self, symbol: str, statement: str) -> None:
        self.conn.execute(
            """DELETE FROM statement_fetches
               WHERE symbol = ? AND statement = ? AND status = 'ok' AND id NOT IN (
                   SELECT id FROM statement_fetches
                   WHERE symbol = ? AND statement = ? AND status = 'ok'
                   ORDER BY fetched_at DESC, id DESC LIMIT ?)""",
            (symbol, statement, symbol, statement, STATEMENT_FETCHES_KEPT),
        )

    def latest_statement_fetch(self, symbol: str, statement: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM statement_fetches WHERE symbol = ? AND statement = ? AND status = 'ok' "
            "ORDER BY fetched_at DESC, id DESC LIMIT 1",
            (symbol, statement),
        ).fetchone()

    def statement_values(self, fetch_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT item, period, value FROM statement_values WHERE fetch_id = ?", (fetch_id,)
        ).fetchall()

    # ── classification, results, scores ─────────────────────────────────────────────────────
    def save_classification(
        self, run_id: int, symbol: str, labels: Mapping[str, str | None]
    ) -> None:
        """labels: label -> reason."""
        self.conn.executemany(
            "INSERT INTO classifications (run_id, symbol, label, reason) VALUES (?, ?, ?, ?)",
            [(run_id, symbol, label, reason) for label, reason in labels.items()],
        )

    def save_results(self, run_id: int, symbol: str, rows: Sequence[Mapping[str, Any]]) -> None:
        """rows: guru, criterion_id, status, and optionally value, threshold, strength, note."""
        self.conn.executemany(
            "INSERT INTO results (run_id, symbol, guru, criterion_id, value, threshold, status, "
            "strength, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    symbol,
                    r["guru"],
                    r["criterion_id"],
                    r.get("value"),
                    r.get("threshold"),
                    r["status"],
                    r.get("strength"),
                    r.get("note"),
                )
                for r in rows
            ],
        )

    def results_for(self, run_id: int, symbol: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM results WHERE run_id = ? AND symbol = ? ORDER BY guru, criterion_id",
            (run_id, symbol),
        ).fetchall()

    def save_score(
        self,
        run_id: int,
        symbol: str,
        kind: str,
        score: float | None,
        coverage: float | None,
        components: Mapping[str, float | None] | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO scores (run_id, symbol, kind, score, coverage) VALUES (?, ?, ?, ?, ?)",
            (run_id, symbol, kind, score, coverage),
        )
        if components:
            self.conn.executemany(
                "INSERT INTO score_components (run_id, symbol, kind, component, value) "
                "VALUES (?, ?, ?, ?, ?)",
                [(run_id, symbol, kind, name, value) for name, value in components.items()],
            )

    def score_history(self, symbol: str, kind: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT s.run_id, r.started_at, s.score, s.coverage FROM scores s "
            "JOIN runs r ON r.id = s.run_id WHERE s.symbol = ? AND s.kind = ? "
            "ORDER BY r.started_at, s.run_id",
            (symbol, kind),
        ).fetchall()

    # ── profiles ────────────────────────────────────────────────────────────────────────────
    def save_profile(
        self,
        symbol: str,
        text: str,
        accession: str,
        model: str,
        prompt_version: str,
        filing_date: str | None = None,
        source_url: str | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO profiles (symbol, text, accession, filing_date, source_url, model, "
            "prompt_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (symbol, accession, prompt_version) DO UPDATE SET "
            "text = excluded.text, model = excluded.model, created_at = excluded.created_at",
            (symbol, text, accession, filing_date, source_url, model, prompt_version, self.now()),
        )

    def latest_profile(self, symbol: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM profiles WHERE symbol = ? ORDER BY filing_date DESC, id DESC LIMIT 1",
            (symbol,),
        ).fetchone()

    # ── dashboard queries ───────────────────────────────────────────────────────────────────
    def latest_analysed_run(self) -> sqlite3.Row | None:
        """The newest run that produced scores (a finished 'ok' run)."""
        return self.conn.execute(
            "SELECT * FROM runs WHERE status = 'ok' AND kind <> 'adhoc' "
            "AND id IN (SELECT run_id FROM scores) "
            "ORDER BY started_at DESC, id DESC LIMIT 1"
        ).fetchone()

    def stock_table(self, run_id: int) -> list[dict[str, Any]]:
        """One dict per analysed stock of the run: company, snapshot multiples, labels, scores."""
        stocks: dict[str, dict[str, Any]] = {}
        for r in self.conn.execute(
            """SELECT c.symbol, c.name, c.sector, c.industry, c.country, c.exchange,
                      s.price, s.market_cap, s.pe_ratio, s.ps_ratio, s.pb_ratio
               FROM screener_snapshots s JOIN companies c ON c.symbol = s.symbol
               WHERE s.run_id = ? AND s.in_screen = 1 ORDER BY c.symbol""",
            (run_id,),
        ):
            stocks[r["symbol"]] = {**dict(r), "labels": [], "scores": {}}
        for r in self.conn.execute(
            "SELECT symbol, label FROM classifications WHERE run_id = ?", (run_id,)
        ):
            if r["symbol"] in stocks:
                stocks[r["symbol"]]["labels"].append(r["label"])
        for r in self.conn.execute(
            "SELECT symbol, kind, score, coverage FROM scores WHERE run_id = ?", (run_id,)
        ):
            if r["symbol"] in stocks:
                stocks[r["symbol"]]["scores"][r["kind"]] = {
                    "score": r["score"],
                    "coverage": r["coverage"],
                }
        return list(stocks.values())

    def result_counts(self, run_id: int) -> dict[str, dict[str, tuple[int, int, int]]]:
        """symbol -> guru -> (passed, computed, total) over the run's criteria results."""
        counts: dict[str, dict[str, tuple[int, int, int]]] = {}
        for r in self.conn.execute(
            """SELECT symbol, guru,
                      SUM(status = 'PASS') AS passed,
                      SUM(status <> 'NA') AS computed,
                      COUNT(*) AS total
               FROM results WHERE run_id = ? GROUP BY symbol, guru""",
            (run_id,),
        ):
            counts.setdefault(r["symbol"], {})[r["guru"]] = (
                int(r["passed"]),
                int(r["computed"]),
                int(r["total"]),
            )
        return counts

    def membership_history(self, limit: int = 500) -> list[sqlite3.Row]:
        """Newest membership events first, with the company name."""
        return self.conn.execute(
            "SELECT e.*, c.name FROM membership_events e LEFT JOIN companies c "
            "ON c.symbol = e.symbol ORDER BY e.created_at DESC, e.id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def latest_run_with_results(self, symbol: str) -> int | None:
        """The newest run in which the symbol was analysed (it may have left the screen since)."""
        row = self.conn.execute(
            "SELECT MAX(run_id) FROM results WHERE symbol = ?", (symbol,)
        ).fetchone()
        return row[0]

    def exited_stocks(self, latest_run_id: int) -> list[sqlite3.Row]:
        """Stocks analysed in an earlier run but not in `latest_run_id`, newest exit first."""
        return self.conn.execute(
            """SELECT g.symbol, c.name, c.sector, g.last_run_id, ru.started_at AS last_at
               FROM (SELECT r.symbol AS symbol, MAX(r.run_id) AS last_run_id
                     FROM results r
                     WHERE r.symbol NOT IN (SELECT symbol FROM scores WHERE run_id = ?)
                       AND r.run_id IN (SELECT id FROM runs WHERE kind <> 'adhoc')
                     GROUP BY r.symbol) g
               JOIN companies c ON c.symbol = g.symbol
               JOIN runs ru ON ru.id = g.last_run_id
               ORDER BY g.last_run_id DESC, g.symbol""",
            (latest_run_id,),
        ).fetchall()

    def adhoc_stocks(self, latest_run_id: int) -> list[sqlite3.Row]:
        """Stocks analysed on request (by ticker) that are not in the latest regular run."""
        return self.conn.execute(
            """SELECT g.symbol, c.name, c.sector, g.last_run_id, ru.started_at AS last_at
               FROM (SELECT r.symbol AS symbol, MAX(r.run_id) AS last_run_id
                     FROM results r
                     WHERE r.run_id IN (SELECT id FROM runs WHERE kind = 'adhoc')
                       AND r.symbol NOT IN (SELECT symbol FROM scores WHERE run_id = ?)
                     GROUP BY r.symbol) g
               JOIN companies c ON c.symbol = g.symbol
               JOIN runs ru ON ru.id = g.last_run_id
               ORDER BY g.last_run_id DESC, g.symbol""",
            (latest_run_id,),
        ).fetchall()

    def is_adhoc_run(self, run_id: int) -> bool:
        row = self.conn.execute("SELECT kind FROM runs WHERE id = ?", (run_id,)).fetchone()
        return bool(row and row["kind"] == "adhoc")

    def set_run_summary(self, run_id: int, summary: str) -> None:
        self.conn.execute("UPDATE runs SET summary = ? WHERE id = ?", (summary, run_id))

    def latest_adhoc_run(self, symbol: str) -> sqlite3.Row | None:
        """The newest ad hoc run for a ticker (its summary starts with the symbol)."""
        return self.conn.execute(
            "SELECT * FROM runs WHERE kind = 'adhoc' AND (summary = ? OR summary LIKE ?) "
            "ORDER BY id DESC LIMIT 1",
            (symbol, f"{symbol}: %"),
        ).fetchone()

    def adhoc_runs_since(self, since_iso: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM runs WHERE kind = 'adhoc' AND started_at >= ?", (since_iso,)
        ).fetchone()[0]

    def sector_pb_values(self, sector: str) -> list[float]:
        """Positive P/B of the sector's stocks in the latest regular run's snapshots."""
        run = self.conn.execute(
            "SELECT MAX(id) FROM runs WHERE kind <> 'adhoc' AND id IN "
            "(SELECT run_id FROM screener_snapshots)"
        ).fetchone()[0]
        if run is None:
            return []
        return [
            r[0]
            for r in self.conn.execute(
                "SELECT s.pb_ratio FROM screener_snapshots s "
                "JOIN companies c ON c.symbol = s.symbol "
                "WHERE s.run_id = ? AND c.sector = ? AND s.pb_ratio > 0",
                (run, sector),
            )
        ]

    def snapshot_for(self, run_id: int, symbol: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM screener_snapshots WHERE run_id = ? AND symbol = ?", (run_id, symbol)
        ).fetchone()

    def recent_runs(self, limit: int = 50) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM runs WHERE kind <> 'adhoc' ORDER BY started_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def score_components_for(self, run_id: int, symbol: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT kind, component, value FROM score_components WHERE run_id = ? AND symbol = ?",
            (run_id, symbol),
        ).fetchall()

    def classification_for(self, run_id: int, symbol: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT label, reason FROM classifications WHERE run_id = ? AND symbol = ?",
            (run_id, symbol),
        ).fetchall()

    def scores_for(self, run_id: int, symbol: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT kind, score, coverage FROM scores WHERE run_id = ? AND symbol = ?",
            (run_id, symbol),
        ).fetchall()

    # ── retention ───────────────────────────────────────────────────────────────────────────
    def apply_retention(self) -> dict[str, int]:
        """Delete data past its retention window. Returns rows deleted per table."""
        now = self._clock()
        cutoff = lambda days: iso(now - timedelta(days=days))  # noqa: E731
        deleted = {}
        with self.transaction():
            deleted["run_log"] = self.conn.execute(
                "DELETE FROM run_log WHERE ts < ?", (cutoff(RUN_LOG_DAYS),)
            ).rowcount
            deleted["screener_snapshots"] = self.conn.execute(
                "DELETE FROM screener_snapshots WHERE captured_at < ?", (cutoff(SNAPSHOT_DAYS),)
            ).rowcount
            deleted["statement_fetches"] = self.conn.execute(
                "DELETE FROM statement_fetches WHERE status <> 'ok' AND fetched_at < ?",
                (cutoff(FAILED_FETCH_DAYS),),
            ).rowcount
        return deleted
