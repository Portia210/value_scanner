"""FastAPI JSON API for the dashboard (E1). The web app only reads the database."""

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from value_scanner.api import schemas, security, views
from value_scanner.jobs import adhoc as adhoc_jobs
from value_scanner.jobs import profiles as profile_jobs
from value_scanner.jobs import scheduler as jobs
from value_scanner.settings import Settings
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

SETTING_DAYS = "days_between_runs"
DEFAULT_DAYS = 7
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class LoginBody(BaseModel):
    password: str


class SettingsBody(BaseModel):
    days_between_runs: int = Field(ge=1, le=60)


def create_app(
    settings: Settings,
    runner: jobs.Runner = jobs.default_runner,
    frontend_dist: Path | None = FRONTEND_DIST,
    adhoc_runner: adhoc_jobs.AdhocRunner = adhoc_jobs.default_adhoc_runner,
    profile_starter=profile_jobs.start_profile,
) -> FastAPI:
    # Local mode: no DASHBOARD_PASSWORD means no login, but only for requests addressed to
    # localhost (the CLI also refuses to bind a non-loopback host in this mode).
    local_mode = not settings.dashboard_password
    if not local_mode and not settings.session_secret:
        raise RuntimeError("SESSION_SECRET must be set when DASHBOARD_PASSWORD is set")
    app = FastAPI(title="Value Scanner", docs_url=None, redoc_url=None)
    signer = security.SessionSigner(settings.session_secret or secrets.token_urlsafe(32))
    limiter = security.LoginLimiter()
    # Schema is created at startup; each request then uses its own connection (threads).
    db.open_database(settings.db_path).close()

    @app.middleware("http")
    async def headers(request: Request, call_next):
        if local_mode and not security.is_local_host(request.headers.get("host", "")):
            return Response("local mode: use http://localhost", status_code=403)
        response = await call_next(request)
        for name, value in security.SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    def get_repo():
        conn = db.connect(settings.db_path, hand_between_threads=True)
        try:
            yield Repository(conn)
        finally:
            conn.close()

    RepoDep = Annotated[Repository, Depends(get_repo)]

    def session_csrf(request: Request) -> str:
        if local_mode:
            return security.LOCAL_CSRF
        csrf = signer.read(request.cookies.get(security.SESSION_COOKIE))
        if csrf is None:
            raise HTTPException(401, "not signed in")
        return csrf

    Session = Annotated[str, Depends(session_csrf)]

    def require_csrf(request: Request, csrf: Session) -> None:
        if not security.password_matches(request.headers.get("x-csrf-token", ""), csrf):
            raise HTTPException(403, "bad CSRF token")

    Csrf = Depends(require_csrf)

    # ── auth ────────────────────────────────────────────────────────────────────────────────
    @app.post("/api/auth/login")
    def login(body: LoginBody, request: Request, response: Response) -> dict[str, str]:
        if local_mode:
            return {"csrf": security.LOCAL_CSRF}
        client = request.client.host if request.client else "?"
        if limiter.blocked(client):
            raise HTTPException(429, "too many attempts, try again later")
        if not security.password_matches(body.password, settings.dashboard_password):
            limiter.fail(client)
            raise HTTPException(401, "wrong password")
        limiter.reset(client)
        cookie, csrf = signer.issue()
        secure = (
            request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        )
        response.set_cookie(
            security.SESSION_COOKIE,
            cookie,
            max_age=security.SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=secure,
        )
        return {"csrf": csrf}

    @app.post("/api/auth/logout", dependencies=[Csrf])
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie(security.SESSION_COOKIE)
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(csrf: Session) -> dict[str, str]:
        return {"csrf": csrf}

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    # ── data ────────────────────────────────────────────────────────────────────────────────
    @app.get("/api/stocks", dependencies=[Depends(session_csrf)])
    def stocks(repo: RepoDep) -> schemas.StocksOut:
        return views.stocks_view(repo)

    @app.get("/api/stocks/{symbol}", dependencies=[Depends(session_csrf)])
    def stock(symbol: str, repo: RepoDep) -> schemas.StockDetailOut:
        detail = views.stock_view(repo, symbol.upper())
        if detail is None:
            raise HTTPException(404, "stock was not analysed in the latest run")
        return detail

    @app.get("/api/criteria", dependencies=[Depends(session_csrf)])
    def criteria() -> schemas.CriteriaOut:
        return views.criteria_view()

    @app.get("/api/history", dependencies=[Depends(session_csrf)])
    def history(repo: RepoDep) -> schemas.HistoryOut:
        return views.history_view(repo)

    @app.get("/api/runs", dependencies=[Depends(session_csrf)])
    def runs(repo: RepoDep) -> list[schemas.RunOut]:
        return [schemas.RunOut(**dict(r)) for r in repo.recent_runs()]

    @app.post("/api/runs", status_code=202, dependencies=[Csrf])
    def start_run() -> dict[str, bool]:
        if not jobs.run_now(settings, runner):
            raise HTTPException(409, "a run is already in progress")
        return {"started": True}

    @app.get("/api/runs/{run_id}/log", dependencies=[Depends(session_csrf)])
    def run_log(run_id: int, repo: RepoDep) -> list[schemas.LogLine]:
        if repo.get_run(run_id) is None:
            raise HTTPException(404, "unknown run")
        return [schemas.LogLine(**dict(r)) for r in repo.run_log(run_id)]

    def settings_view(repo: Repository) -> schemas.SettingsOut:
        days = int(repo.get_setting(SETTING_DAYS, str(DEFAULT_DAYS)))
        last = repo.last_successful_run()
        nxt = None
        if last is not None:
            started = datetime.strptime(last["started_at"], "%Y-%m-%dT%H:%M:%SZ")
            due = started.replace(tzinfo=UTC) + timedelta(days=days)
            nxt = due.strftime("%Y-%m-%dT%H:%M:%SZ")
        return schemas.SettingsOut(
            days_between_runs=days,
            last_run_at=last["started_at"] if last else None,
            next_run_at=nxt,
        )

    @app.get("/api/settings", dependencies=[Depends(session_csrf)])
    def get_settings(repo: RepoDep) -> schemas.SettingsOut:
        return settings_view(repo)

    @app.put("/api/settings", dependencies=[Csrf])
    def put_settings(body: SettingsBody, repo: RepoDep) -> schemas.SettingsOut:
        repo.set_setting(SETTING_DAYS, str(body.days_between_runs))
        return settings_view(repo)

    # ── analysis of one ticker on request (E8) ─────────────────────────────────────────────
    def analyses_left(repo: Repository) -> int:
        since = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return max(0, adhoc_jobs.DAILY_LIMIT - repo.adhoc_runs_since(since))

    @app.post("/api/analyses", status_code=202, dependencies=[Csrf])
    def start_analysis(body: schemas.AnalysisBody, repo: RepoDep) -> dict[str, str]:
        symbol = adhoc_jobs.normalise(body.symbol)
        if symbol is None:
            raise HTTPException(422, "not a ticker")
        if analyses_left(repo) == 0:
            raise HTTPException(429, f"daily limit of {adhoc_jobs.DAILY_LIMIT} analyses reached")
        if not adhoc_jobs.start_adhoc(settings, symbol, adhoc_runner):
            raise HTTPException(409, "a run is already in progress")
        return {"symbol": symbol}

    @app.get("/api/analyses/{symbol}", dependencies=[Depends(session_csrf)])
    def analysis_status(symbol: str, repo: RepoDep) -> schemas.AnalysisStatus:
        symbol = (adhoc_jobs.normalise(symbol) or "").upper()
        run = repo.latest_adhoc_run(symbol) if symbol else None
        left = analyses_left(repo)
        if run is None:
            return schemas.AnalysisStatus(symbol=symbol, status="none", analyses_left_today=left)
        summary = run["summary"] or ""
        message = summary.split(": ", 1)[1] if ": " in summary else None
        return schemas.AnalysisStatus(
            symbol=symbol,
            status=run["status"] if run["status"] in ("running", "ok", "blocked") else "failed",
            message=message,
            progress_done=run["progress_done"],
            progress_total=run["progress_total"],
            started_at=run["started_at"],
            analyses_left_today=left,
        )

    @app.post("/api/profiles/{symbol}", status_code=202, dependencies=[Csrf])
    def start_profile(symbol: str) -> dict[str, str]:
        symbol = adhoc_jobs.normalise(symbol)
        if symbol is None:
            raise HTTPException(422, "not a ticker")
        if not (settings.google_api_key and settings.my_email):
            raise HTTPException(503, "profiles are not configured (GOOGLE_API_KEY, MY_EMAIL)")
        if profile_starter(settings, symbol) is False:
            raise HTTPException(409, "a profile for this stock is already being created")
        return {"symbol": symbol}

    @app.get("/api/profiles/{symbol}/status", dependencies=[Depends(session_csrf)])
    def profile_status(symbol: str) -> schemas.ProfileJob:
        symbol = (adhoc_jobs.normalise(symbol) or "").upper()
        return schemas.ProfileJob(symbol=symbol, status=profile_jobs.profile_job_status(symbol))

    # ── the built frontend (Vite output), served from the same origin ──────────────────────
    if frontend_dist is not None and (frontend_dist / "index.html").is_file():
        root = frontend_dist.resolve()
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404, "unknown endpoint")
            candidate = (root / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(root / "index.html")

    return app


def openapi_schema() -> dict:
    """The OpenAPI schema without touching any database (used to generate frontend types)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(db_path=Path(tmp) / "schema.db")
        return create_app(settings, frontend_dist=None).openapi()
