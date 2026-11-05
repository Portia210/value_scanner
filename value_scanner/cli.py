"""Command line entry point: `python -m value_scanner <command>`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from value_scanner import __version__
from value_scanner.settings import load_settings

# command -> (help text, ROADMAP task that implements it)
_PENDING = {
    "serve": ("Serve the dashboard and the scheduler", "E1"),
    "docs": ("Generate docs/criteria/*.md from the criteria definitions", "C10"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m value_scanner",
        description="Value-investing stock scanner. All settings come from environment variables "
        "(see .env.example); all data lives in one SQLite file at DB_PATH.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for name, (text, task) in _PENDING.items():
        sub.add_parser(name, help=f"{text} (not implemented yet: ROADMAP {task})")
    run = sub.add_parser("run", help="Run a full scan end to end; alerts go to MY_EMAIL")
    run.add_argument(
        "--limit", type=int, metavar="N", help="only download statements for the first N stocks"
    )
    sub.add_parser(
        "config", help="Show the effective settings (secrets are only reported as set/unset)"
    )
    return parser


def _show_config() -> int:
    s = load_settings(load_dotenv_file=True)
    print(f"DB_PATH            = {s.db_path}")
    for name in (
        "my_email",
        "dashboard_password",
        "session_secret",
        "google_api_key",
        "smtp_host",
        "smtp_user",
        "smtp_password",
    ):
        print(f"{name.upper():18} = {'set' if getattr(s, name) else 'unset'}")
    return 0


def _run(limit: int | None) -> int:
    from value_scanner.jobs.pipeline import run_scan
    from value_scanner.storage import db
    from value_scanner.storage.repo import Repository

    settings = load_settings(load_dotenv_file=True)
    repo = Repository(db.open_database(settings.db_path))
    if repo.mark_interrupted_runs():
        print("marked a run left over from a crash as interrupted")
    outcome = run_scan(repo, settings, "cli", limit=limit)
    print(f"{outcome.status}: {outcome.summary}")
    return {"ok": 0, "locked": 3, "blocked": 3}.get(outcome.status, 1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "config":
        return _show_config()
    if args.command == "run":
        return _run(args.limit)
    _, task = _PENDING[args.command]
    print(f"'{args.command}' is not implemented yet (ROADMAP {task}).", file=sys.stderr)
    return 2
