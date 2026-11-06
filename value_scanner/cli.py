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
    prof = sub.add_parser(
        "profiles", help="Write/refresh Hebrew business profiles (SEC annual report -> Gemini)"
    )
    prof.add_argument("symbols", nargs="*", help="symbols; default: the candidates of the last run")
    sub.add_parser("test-alert", help="Send one test email to MY_EMAIL through the configured SMTP")
    sub.add_parser("openapi", help="Print the API's OpenAPI schema (source of the frontend types)")
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


def _profiles(symbols: list[str]) -> int:
    from value_scanner.jobs.profiles import candidate_symbols, refresh_profiles
    from value_scanner.storage import db
    from value_scanner.storage.repo import Repository

    settings = load_settings(load_dotenv_file=True)
    repo = Repository(db.open_database(settings.db_path))
    symbols = [s.upper() for s in symbols] or candidate_symbols(repo)
    summary = refresh_profiles(repo, settings, symbols)
    print(
        f"created {len(summary.created)}, fresh {len(summary.fresh)}, "
        f"unsupported {len(summary.unsupported)}, failed {len(summary.failed)}"
    )
    return 1 if summary.failed else 0


def _test_alert() -> int:
    from value_scanner.jobs.alerts import send_test_alert

    try:
        send_test_alert(load_settings(load_dotenv_file=True))
    except Exception as exc:  # noqa: BLE001 - report the type, never the (secret-bearing) details
        print(f"test alert FAILED: {type(exc).__name__}")
        return 1
    print("test alert sent to MY_EMAIL")
    return 0


def _serve(parser: argparse.ArgumentParser, host: str, port: int) -> int:
    import uvicorn

    from value_scanner.api.app import create_app
    from value_scanner.api.security import is_loopback_bind
    from value_scanner.jobs.scheduler import start_scheduler

    settings = load_settings(load_dotenv_file=True)
    if not settings.dashboard_password and not is_loopback_bind(host):
        parser.error(
            "DASHBOARD_PASSWORD is not set (local mode): serve only on 127.0.0.1, "
            "or set DASHBOARD_PASSWORD and SESSION_SECRET"
        )
    app = create_app(settings)
    scheduler = start_scheduler(settings)
    try:
        uvicorn.run(app, host=host, port=port)
    finally:
        scheduler.shutdown(wait=False)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "config":
        return _show_config()
    if args.command == "serve":
        return _serve(parser, args.host, args.port)
    if args.command == "docs":
        from value_scanner.analysis.docs import write_all

        for path in write_all():
            print(f"wrote {path}")
        return 0
    if args.command == "profiles":
        return _profiles(args.symbols)
    if args.command == "test-alert":
        return _test_alert()
    if args.command == "openapi":
        import json

        from value_scanner.api.app import openapi_schema

        print(json.dumps(openapi_schema(), indent=2, sort_keys=True))
        return 0
    if args.command == "run":
        return _run(args.limit)
    parser.error(f"unknown command {args.command}")
    return 2
