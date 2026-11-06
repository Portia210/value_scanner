"""Analysis of one ticker on request (E8): any stock of the screener, not only those in the screen.

It is a run of kind 'adhoc': same lock as a scan (one job against the site at a time), own results
in the regular tables, never counted by the scheduler, the dashboard's run or the membership
history. Steps: the stock's row from the screener JSON -> its statements (slow, only what is stale)
-> the same criteria, classification and scores as in a scan.
"""

from __future__ import annotations

import re
import statistics
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from value_scanner.jobs.alerts import send_pending_alerts
from value_scanner.jobs.analyze import analyse_and_store
from value_scanner.jobs.pipeline import RunOutcome
from value_scanner.jobs.refresh import Pacing, download_statements
from value_scanner.jobs.universe import SNAPSHOT_FIELDS
from value_scanner.settings import Settings
from value_scanner.sources.screener import Blocked, Universe, evaluate, fetch_universe
from value_scanner.sources.stockanalysis import StatementFetcher
from value_scanner.storage import db
from value_scanner.storage.repo import Repository, RunAlreadyRunning

DAILY_LIMIT = 20  # analyses per rolling 24 hours: keeps the site's rate limiter calm
SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")

AdhocRunner = Callable[[Settings, str], RunOutcome]


def normalise(symbol: str) -> str | None:
    """Upper-case ticker if it looks like one, else None."""
    symbol = symbol.strip().upper()
    return symbol if SYMBOL.match(symbol) else None


def over_daily_limit(repo: Repository, now: datetime | None = None) -> bool:
    since = (now or datetime.now(UTC)) - timedelta(days=1)
    return repo.adhoc_runs_since(since.strftime("%Y-%m-%dT%H:%M:%SZ")) >= DAILY_LIMIT


def analyse_ticker(
    repo: Repository,
    settings: Settings,
    symbol: str,
    *,
    fetch: Callable[[], Universe] = fetch_universe,
    fetcher: StatementFetcher | None = None,
    pacing: Pacing | None = None,
    sleep: Callable[[float], None] = time.sleep,
    sender=None,
) -> RunOutcome:
    try:
        run_id = repo.start_run("adhoc")
    except RunAlreadyRunning:
        return RunOutcome(None, "locked", "another run is in progress")
    repo.set_run_summary(run_id, symbol)  # the status endpoint finds the run by this
    status, message, error = "failed", "", None
    try:
        stock = {k.upper(): v for k, v in fetch().stocks.items()}.get(symbol)
        if stock is None:
            message = "unknown ticker (not in the StockAnalysis screener)"
            return RunOutcome(run_id, "failed", f"{symbol}: {message}")
        outcome = evaluate(stock)
        with repo.transaction():
            repo.upsert_company(
                symbol,
                name=stock.name,
                country=stock.get("country"),
                exchange=stock.get("exchange"),
                sector=stock.get("sector"),
                industry=stock.get("industry"),
            )
            fields = {col: stock.get(key) for key, col in SNAPSHOT_FIELDS.items()}
            repo.save_snapshot(
                run_id,
                symbol,
                {**fields, "in_screen": int(outcome.passed), "filters_failed": len(outcome.failed)},
            )
        downloads = download_statements(
            repo,
            run_id,
            fetcher or StatementFetcher(sleep=sleep),
            [symbol],
            pacing=pacing,
            sleep=sleep,
            on_progress=lambda done, total: repo.update_progress(run_id, done, total),
        )
        if repo.latest_statement_fetch(symbol, "income") is None:
            message = "no financial statements available for this ticker"
            if downloads.failures:
                message += f" ({downloads.failures[0][:80]})"
            return RunOutcome(run_id, "failed", f"{symbol}: {message}")
        company = repo.get_company(symbol)
        snap = repo.snapshot_for(run_id, symbol)
        pbs = repo.sector_pb_values(company["sector"] or "") if company["sector"] else []
        median = statistics.median(pbs) if len(pbs) >= 3 else None
        with repo.transaction():
            quality, opportunity = analyse_and_store(repo, run_id, symbol, company, snap, median)
        status = "ok"
        message = "ok" + ("" if quality is None else f" · quality {round(quality * 100)}")
        return RunOutcome(run_id, "ok", f"{symbol}: {message}")
    except Blocked as exc:
        status, message, error = "blocked", "blocked by StockAnalysis, try again later", str(exc)
        repo.add_alert("blocked", "StockAnalysis blocked a ticker analysis", str(exc), run_id)
        return RunOutcome(run_id, "blocked", f"{symbol}: {message}")
    except Exception as exc:
        status, message = "failed", "unexpected error"
        error = f"{type(exc).__name__}: {exc}"
        repo.add_alert("run_failed", f"Ticker analysis of {symbol} crashed", error, run_id)
        return RunOutcome(run_id, "failed", f"{symbol}: {message}")
    finally:
        repo.finish_run(run_id, status, f"{symbol}: {message}", error)
        send_pending_alerts(repo, settings, sender)


def default_adhoc_runner(settings: Settings, symbol: str) -> RunOutcome:
    conn = db.connect(settings.db_path)
    try:
        return analyse_ticker(Repository(conn), settings, symbol)
    finally:
        conn.close()


def start_adhoc(
    settings: Settings, symbol: str, runner: AdhocRunner = default_adhoc_runner
) -> bool:
    """Start the analysis in a background thread. False if a run is already in progress."""
    conn = db.connect(settings.db_path)
    try:
        if conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
            return False
    finally:
        conn.close()
    threading.Thread(target=runner, args=(settings, symbol), daemon=True).start()
    return True
