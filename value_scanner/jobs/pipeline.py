"""One full scan, end to end, without a human at the keyboard (B4).

universe (screener JSON) -> statements (slow, only what is stale) -> [criteria engine: C-phase]
-> retention -> alert emails. Every outcome ends the run row in a final status; a crash or Ctrl-C
leaves it 'interrupted', never 'running'.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from value_scanner.jobs.alerts import Sender, send_pending_alerts
from value_scanner.jobs.refresh import DownloadSummary, Pacing, download_statements
from value_scanner.jobs.universe import UniverseResult, refresh_universe
from value_scanner.settings import Settings
from value_scanner.sources.screener import Blocked, StructureChanged, Universe, fetch_universe
from value_scanner.sources.stockanalysis import StatementFetcher
from value_scanner.storage.repo import Repository, RunAlreadyRunning

# More than this share of downloads failing is "extraction failed" and sends an alert.
MAX_FAILURE_SHARE = 0.2


@dataclass
class RunOutcome:
    run_id: int | None
    status: str  # ok | failed | blocked | interrupted | locked
    summary: str


def run_scan(
    repo: Repository,
    settings: Settings,
    kind: str = "cli",
    *,
    limit: int | None = None,
    fetch: Callable[[], Universe] = fetch_universe,
    fetcher: StatementFetcher | None = None,
    pacing: Pacing | None = None,
    sleep: Callable[[float], None] = time.sleep,
    sender: Sender | None = None,
    log: Callable[[str], None] = print,
) -> RunOutcome:
    try:
        run_id = repo.start_run(kind)
    except RunAlreadyRunning:
        return RunOutcome(None, "locked", "another run is in progress")

    def note(level: str, message: str) -> None:
        repo.log(run_id, level, message)
        log(f"[run {run_id}] {message}")

    status, summary, error = "failed", "", None
    try:
        note("info", "fetching the screener universe")
        universe: UniverseResult = refresh_universe(repo, run_id, fetch)
        note(
            "info",
            f"universe {universe.total}: {len(universe.in_screen)} in screen, "
            f"{len(universe.almost)} almost, +{len(universe.entered)}/-{len(universe.exited)}",
        )

        symbols = sorted(universe.in_screen)[:limit]
        note("info", f"downloading statements for {len(symbols)} stocks (only what is stale)")
        try:
            downloads = download_statements(
                repo,
                run_id,
                fetcher or StatementFetcher(sleep=sleep),
                symbols,
                pacing=pacing,
                sleep=sleep,
                on_progress=lambda done, total: _progress(repo, run_id, done, total),
            )
        except Blocked as exc:
            repo.add_alert(
                "blocked", "StockAnalysis blocked the statement downloads", str(exc), run_id
            )
            raise
        attempted = downloads.ok + downloads.failed + downloads.no_table
        if attempted and (downloads.failed + downloads.no_table) / attempted > MAX_FAILURE_SHARE:
            repo.add_alert(
                "extraction_failed",
                "Many statement downloads failed",
                "\n".join(downloads.failures[:30]),
                run_id,
            )
        note("info", "criteria and scores: not built yet (ROADMAP C-phase)")
        repo.apply_retention()
        status, summary = "ok", _summary(universe, downloads)
    except Blocked as exc:
        status, summary, error = "blocked", "blocked by StockAnalysis", str(exc)
    except StructureChanged as exc:
        status, summary, error = "failed", "screener structure changed", str(exc)
    except (KeyboardInterrupt, SystemExit):
        status, summary = "interrupted", "interrupted"
        raise
    except Exception as exc:
        status, summary, error = "failed", "unexpected error", f"{type(exc).__name__}: {exc}"
        repo.add_alert("run_failed", "Scan crashed", error, run_id)
    finally:
        repo.finish_run(run_id, status, summary, error)
        note("info" if status == "ok" else "error", f"finished: {status} - {summary}")
        send_pending_alerts(repo, settings, sender)
    return RunOutcome(run_id, status, summary)


def _progress(repo: Repository, run_id: int, done: int, total: int) -> None:
    repo.update_progress(run_id, done, total)


def _summary(universe: UniverseResult, downloads: DownloadSummary) -> str:
    return (
        f"{len(universe.in_screen)} in screen; statements ok={downloads.ok} "
        f"failed={downloads.failed} no_table={downloads.no_table} "
        f"fresh-skipped={downloads.skipped_fresh}"
    )
