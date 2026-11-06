"""Which statements to download, and the slow, bounded download loop (B1, D18, R5).

R5 (preferred): the screener's `lastReportDate` (period end of the latest report on StockAnalysis)
is stored with every download; a statement is downloaded again when the screener now shows a newer
one. If the page has not caught up (identical values) the old date is kept, so the next run tries
again, at most `NEW_REPORT_TRIES` times. D18 (fallback, when either date is unknown): a new stock
immediately; after `lastEarningsDate` passes, try 1, 3 and 7 days later until a changed table
appears. Both: a long backstop refresh (`FULL_REFRESH_DAYS`) for retroactive corrections.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from value_scanner.sources.screener import Blocked
from value_scanner.sources.stockanalysis import DEFAULT_STATEMENTS, StatementFetcher
from value_scanner.storage.repo import Repository

FULL_REFRESH_DAYS = 120  # backstop; D18 used 45 before R5
NEW_REPORT_TRIES = 3  # R5: downloads that may find the page still old before accepting it
ADOPT_AFTER_EARNINGS_DAYS = 3  # R5: a download made this long after earnings counts as current
EARNINGS_RETRY_OFFSETS = (1, 3, 7)  # days after lastEarningsDate


def refresh_reason(
    now: datetime,
    fetch_times: list[datetime],
    last_earnings: date | None,
    changed_since_earnings: bool,
) -> str | None:
    """Why a statement should be downloaded now, or None.

    `fetch_times`: times of the successful downloads, newest first.
    `changed_since_earnings`: a download after `last_earnings` already differs from the newest
    one made on or before it (the new period has appeared).
    """
    if not fetch_times:
        return "new"
    if now - fetch_times[0] >= timedelta(days=FULL_REFRESH_DAYS):
        return "full_refresh"
    if last_earnings is None or last_earnings > now.date():
        return None
    baseline_exists = any(t.date() <= last_earnings for t in fetch_times)
    if not baseline_exists or changed_since_earnings:
        return None
    attempts = sum(1 for t in fetch_times if t.date() > last_earnings)
    if attempts >= len(EARNINGS_RETRY_OFFSETS):
        return None
    due = last_earnings + timedelta(days=EARNINGS_RETRY_OFFSETS[attempts])
    return f"earnings_try_{attempts + 1}" if now.date() >= due else None


def _fetch_times(repo: Repository, symbol: str, statement: str) -> list[tuple[int, datetime]]:
    rows = repo.conn.execute(
        "SELECT id, fetched_at FROM statement_fetches WHERE symbol = ? AND statement = ? "
        "AND status = 'ok' ORDER BY fetched_at DESC, id DESC",
        (symbol, statement),
    ).fetchall()
    return [
        (r["id"], datetime.strptime(r["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC))
        for r in rows
    ]


def _values(repo: Repository, fetch_id: int) -> set[tuple[str, str, float | None]]:
    return {(r["item"], r["period"], r["value"]) for r in repo.statement_values(fetch_id)}


def _day(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _adopt_baseline(
    repo: Repository, fetch: Any, seen: date, last_earnings: date | None
) -> date | None:
    """R5 transition: a download made before report dates were stored has none. Trust it as current
    only when it was made at least `ADOPT_AFTER_EARNINGS_DAYS` after the latest earnings date (so
    the site had time to publish the report); otherwise leave it unknown and use the D18 rules."""
    fetched = datetime.strptime(fetch["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").date()
    if last_earnings is not None and fetched < last_earnings + timedelta(
        days=ADOPT_AFTER_EARNINGS_DAYS
    ):
        return None
    repo.set_fetch_report_date(fetch["id"], seen.isoformat())
    return seen


def statement_refresh_reason(
    repo: Repository, symbol: str, statement: str, now: datetime, last_earnings: date | None
) -> str | None:
    fetches = _fetch_times(repo, symbol, statement)
    if not fetches:
        return "new"
    seen = _day(repo.latest_report_date(symbol))
    latest = repo.latest_statement_fetch(symbol, statement)
    have = _day(latest["report_date"])
    if have is None and seen is not None:
        have = _adopt_baseline(repo, latest, seen, last_earnings)
    if seen is not None and have is not None:
        if seen > have:
            return "new_report"
        if now - fetches[0][1] >= timedelta(days=FULL_REFRESH_DAYS):
            return "full_refresh"
        return None
    changed = False
    if last_earnings is not None:
        after = [f for f in fetches if f[1].date() > last_earnings]
        before = [f for f in fetches if f[1].date() <= last_earnings]
        if after and before:
            changed = _values(repo, after[0][0]) != _values(repo, before[0][0])
    return refresh_reason(now, [t for _, t in fetches], last_earnings, changed)


def _report_date_to_store(
    repo: Repository, symbol: str, statement: str, reason: str, rows: list
) -> str | None:
    """The `lastReportDate` to record with a finished download. For a `new_report` download whose
    values equal the previous download the page has not caught up yet: keep the old date so the next
    run retries, until `NEW_REPORT_TRIES` downloads have been made since the new date appeared."""
    seen = repo.latest_report_date(symbol)
    if reason != "new_report" or seen is None:
        return seen
    previous = repo.latest_statement_fetch(symbol, statement)
    if previous is None or set(rows) != _values(repo, previous["id"]):
        return seen
    tries = repo.downloads_since_report_date_appeared(symbol, statement, seen)
    return seen if tries + 1 >= NEW_REPORT_TRIES else previous["report_date"]


@dataclass
class DownloadSummary:
    ok: int = 0
    failed: int = 0
    no_table: int = 0
    skipped_fresh: int = 0
    failures: list[str] = field(default_factory=list)  # "SYMBOL/statement: reason"


@dataclass
class Pacing:
    """Slow on purpose: one request at a time, 3-6 s apart, a long rest every few dozen."""

    pause: tuple[float, float] = (3.0, 6.0)
    rest_every: tuple[int, int] = (30, 60)  # requests between long rests
    rest: tuple[float, float] = (60.0, 120.0)
    block_wait: float = 600.0  # after a challenge/429: stop this long, then try again
    max_blocks_in_a_row: int = 3  # abort the batch after this many blocks without a success


def download_statements(
    repo: Repository,
    run_id: int | None,
    fetcher: StatementFetcher,
    symbols: Iterable[str],
    *,
    statements: Iterable[str] = DEFAULT_STATEMENTS,
    pacing: Pacing | None = None,
    now: Callable[[], datetime] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> DownloadSummary:
    """Download what is stale for each symbol. One failed stock never stops the run; repeated
    blocking does (raises Blocked after the waits are exhausted). Nothing is bypassed."""
    pacing = pacing or Pacing()
    rng = rng or random.Random()
    now = now or repo._clock
    statements = tuple(statements)
    summary = DownloadSummary()

    work = []
    for symbol in symbols:
        last_earnings = _last_earnings(repo, symbol)
        for statement in statements:
            reason = statement_refresh_reason(repo, symbol, statement, now(), last_earnings)
            if reason:
                work.append((symbol, statement, reason))
            else:
                summary.skipped_fresh += 1

    requests_since_rest = 0
    next_rest = rng.randint(*pacing.rest_every)
    blocks_in_a_row = 0
    for done, (symbol, statement, reason) in enumerate(work, start=1):
        while True:
            outcome = fetcher.fetch(symbol, statement)
            requests_since_rest += 1
            if outcome.status != "blocked":
                blocks_in_a_row = 0
                break
            blocks_in_a_row += 1
            repo.save_statement_fetch(symbol, statement, "stockanalysis", "blocked", run_id=run_id)
            if run_id:
                repo.log(run_id, "warning", f"blocked at {symbol}/{statement} ({reason}); resting")
            if blocks_in_a_row >= pacing.max_blocks_in_a_row:
                raise Blocked(f"blocked {blocks_in_a_row} times in a row at {symbol}/{statement}")
            sleep(pacing.block_wait)

        report_date = (
            _report_date_to_store(repo, symbol, statement, reason, outcome.rows)
            if outcome.status == "ok"
            else None
        )
        repo.save_statement_fetch(
            symbol,
            statement,
            "stockanalysis",
            outcome.status,
            outcome.rows,
            outcome.latest_period,
            run_id,
            report_date,
        )
        if outcome.status == "ok":
            summary.ok += 1
        else:
            summary.no_table += outcome.status == "no_table"
            summary.failed += outcome.status == "failed"
            summary.failures.append(f"{symbol}/{statement}: {outcome.status} {outcome.detail[:80]}")
            repo.add_parse_failure(
                "stockanalysis", outcome.status, outcome.detail, symbol=symbol, run_id=run_id
            )
        if on_progress:
            on_progress(done, len(work))
        if done == len(work):
            break
        if requests_since_rest >= next_rest:
            sleep(rng.uniform(*pacing.rest))
            requests_since_rest, next_rest = 0, rng.randint(*pacing.rest_every)
        else:
            sleep(rng.uniform(*pacing.pause))
    return summary


def _last_earnings(repo: Repository, symbol: str) -> date | None:
    row = repo.conn.execute(
        "SELECT last_earnings_date FROM screener_snapshots WHERE symbol = ? "
        "AND last_earnings_date IS NOT NULL ORDER BY captured_at DESC, id DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    return date.fromisoformat(row["last_earnings_date"]) if row else None
