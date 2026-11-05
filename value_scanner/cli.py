"""Command line entry point: `python -m value_scanner <command>`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from value_scanner import __version__
from value_scanner.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m value_scanner",
        description="Value-investing stock scanner. All settings come from environment variables "
        "(see .env.example); all data lives in one SQLite file at DB_PATH.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    run = sub.add_parser("run", help="Run a full scan end to end; alerts go to MY_EMAIL")
    run.add_argument(
        "--limit", type=int, metavar="N", help="only download statements for the first N stocks"
    )
    serve = sub.add_parser("serve", help="Serve the dashboard API and run the scheduler")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    sub.add_parser("docs", help="Write docs/criteria/*.md from the criteria definitions")
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
    if args.command == "serve":
        import uvicorn

        from value_scanner.api.app import create_app

        uvicorn.run(
            create_app(load_settings(load_dotenv_file=True)), host=args.host, port=args.port
        )
        return 0
    if args.command == "docs":
        from value_scanner.analysis.docs import write_all

        for path in write_all():
            print(f"wrote {path}")
        return 0
    if args.command == "run":
        return _run(args.limit)
    parser.error(f"unknown command {args.command}")
    return 2
