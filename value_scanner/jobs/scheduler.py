"""Scheduling (E5): every 15 minutes check whether a scan is due; "run now" from the dashboard.

A scan is due when `days_between_runs` days have passed since the last *successful* run. After
a failed or blocked run we wait RETRY_AFTER before trying again, so a block is never hammered.
The database lock (one 'running' row) makes two simultaneous runs impossible.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from value_scanner.jobs.pipeline import RunOutcome, run_scan
from value_scanner.settings import Settings
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

DEFAULT_DAYS = 7
CHECK_EVERY_MINUTES = 15
RETRY_AFTER = timedelta(hours=6)
SETTING_DAYS = "days_between_runs"

Runner = Callable[[Settings, str], RunOutcome]


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def is_due(repo: Repository, now: datetime) -> bool:
    if repo.conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
        return False
    last = repo.recent_runs(1)
    if (
        last
        and last[0]["status"] != "ok"
        and last[0]["finished_at"]
        and now - _parse(last[0]["finished_at"]) < RETRY_AFTER
    ):
        return False
    ok = repo.last_successful_run()
    if ok is None:
        return True
    days = int(repo.get_setting(SETTING_DAYS, str(DEFAULT_DAYS)))
    return now - _parse(ok["started_at"]) >= timedelta(days=days)


def default_runner(settings: Settings, kind: str) -> RunOutcome:
    conn = db.connect(settings.db_path)
    try:
        return run_scan(Repository(conn), settings, kind)
    finally:
        conn.close()


def tick(
    settings: Settings,
    runner: Runner = default_runner,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> RunOutcome | None:
    """One scheduler check: start a scheduled run if one is due."""
    conn = db.open_database(settings.db_path)
    try:
        due = is_due(Repository(conn), now())
    finally:
        conn.close()
    return runner(settings, "scheduled") if due else None


def run_now(settings: Settings, runner: Runner = default_runner) -> bool:
    """Start a manual run in a background thread. False if a run is already in progress."""
    conn = db.connect(settings.db_path)
    try:
        if conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone():
            return False
    finally:
        conn.close()
    threading.Thread(target=runner, args=(settings, "manual"), daemon=True).start()
    return True


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    """Mark runs left over from a crash as interrupted, then start the periodic check."""
    conn = db.open_database(settings.db_path)
    try:
        Repository(conn).mark_interrupted_runs()
    finally:
        conn.close()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        tick,
        "interval",
        minutes=CHECK_EVERY_MINUTES,
        args=[settings],
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(UTC) + timedelta(seconds=30),
    )
    scheduler.start()
    return scheduler
