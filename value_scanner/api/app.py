"""FastAPI JSON API for the dashboard (E1). The web app only reads the database."""

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from value_scanner.analysis.scoring import CANDIDATE_OPPORTUNITY, CANDIDATE_QUALITY
from value_scanner.api import security
from value_scanner.settings import Settings
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

SETTING_DAYS = "days_between_runs"
DEFAULT_DAYS = 7


class LoginBody(BaseModel):
    password: str


class SettingsBody(BaseModel):
    days_between_runs: int = Field(ge=1, le=60)


def create_app(settings: Settings) -> FastAPI:
    if not settings.dashboard_password or not settings.session_secret:
        raise RuntimeError("DASHBOARD_PASSWORD and SESSION_SECRET must be set")
    app = FastAPI(title="Value Scanner", docs_url=None, redoc_url=None)
    signer = security.SessionSigner(settings.session_secret)
    limiter = security.LoginLimiter()
    # Schema is created at startup; each request then uses its own connection (threads).
    db.open_database(settings.db_path).close()

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in security.SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    def get_repo():
        conn = db.connect(settings.db_path)
        try:
            yield Repository(conn)
        finally:
            conn.close()

    RepoDep = Annotated[Repository, Depends(get_repo)]

    def session_csrf(request: Request) -> str:
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
    def stocks(repo: RepoDep) -> dict[str, Any]:
        run = repo.latest_analysed_run()
        if run is None:
            return {"run": None, "stocks": []}
        rows = repo.stock_table(run["id"])
        for row in rows:
            q = (row["scores"].get("quality") or {}).get("score")
            o = (row["scores"].get("opportunity") or {}).get("score")
            row["candidate"] = (
                q is not None
                and o is not None
                and q >= CANDIDATE_QUALITY
                and o >= CANDIDATE_OPPORTUNITY
            )
        return {"run": {"id": run["id"], "started_at": run["started_at"]}, "stocks": rows}

    @app.get("/api/stocks/{symbol}", dependencies=[Depends(session_csrf)])
    def stock(symbol: str, repo: RepoDep) -> dict[str, Any]:
        symbol = symbol.upper()
        company = repo.get_company(symbol)
        run = repo.latest_analysed_run()
        if company is None or run is None:
            raise HTTPException(404, "unknown stock")
        results = [dict(r) for r in repo.results_for(run["id"], symbol)]
        if not results:
            raise HTTPException(404, "stock was not analysed in the latest run")
        return {
            "company": dict(company),
            "run": {"id": run["id"], "started_at": run["started_at"]},
            "labels": [dict(r) for r in repo.classification_for(run["id"], symbol)],
            "results": results,
            "scores": {
                r["kind"]: {"score": r["score"], "coverage": r["coverage"]}
                for r in repo.scores_for(run["id"], symbol)
            },
            "components": {
                r["component"]: r["value"] for r in repo.score_components_for(run["id"], symbol)
            },
            "history": {
                kind: [dict(h) for h in repo.score_history(symbol, kind)]
                for kind in ("quality", "opportunity")
            },
            "membership_events": [dict(e) for e in repo.membership_events(symbol)],
        }

    @app.get("/api/runs", dependencies=[Depends(session_csrf)])
    def runs(repo: RepoDep) -> list[dict[str, Any]]:
        return [dict(r) for r in repo.recent_runs()]

    @app.get("/api/runs/{run_id}/log", dependencies=[Depends(session_csrf)])
    def run_log(run_id: int, repo: RepoDep) -> list[dict[str, Any]]:
        if repo.get_run(run_id) is None:
            raise HTTPException(404, "unknown run")
        return [dict(r) for r in repo.run_log(run_id)]

    @app.get("/api/settings", dependencies=[Depends(session_csrf)])
    def get_settings(repo: RepoDep) -> dict[str, int]:
        return {SETTING_DAYS: int(repo.get_setting(SETTING_DAYS, str(DEFAULT_DAYS)))}

    @app.put("/api/settings", dependencies=[Csrf])
    def put_settings(body: SettingsBody, repo: RepoDep) -> dict[str, int]:
        repo.set_setting(SETTING_DAYS, str(body.days_between_runs))
        return {SETTING_DAYS: body.days_between_runs}

    return app
