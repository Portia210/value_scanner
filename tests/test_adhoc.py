import httpx
import pytest
from fastapi.testclient import TestClient

from tests.factories import screener_json, statement_html
from tests.test_analyze import run_with, seed
from value_scanner.api.app import create_app
from value_scanner.jobs import adhoc
from value_scanner.jobs.analyze import analyse_run
from value_scanner.jobs.pipeline import RunOutcome
from value_scanner.jobs.refresh import Pacing
from value_scanner.jobs.scheduler import is_due
from value_scanner.settings import load_settings
from value_scanner.sources.screener import Blocked, parse_universe
from value_scanner.sources.stockanalysis import HEADERS, StatementFetcher
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

SETTINGS = load_settings({"DB_PATH": ":memory:"})
NO_PAUSE = Pacing(pause=(0, 0), block_wait=0, workers=1)


@pytest.fixture
def repo():
    return Repository(db.open_database(":memory:"))


def universe_of(stocks):
    return lambda: parse_universe(*screener_json(stocks))


def fetcher(handler=None):
    handler = handler or (lambda r: httpx.Response(200, text=statement_html()))
    client = httpx.Client(transport=httpx.MockTransport(handler), headers=HEADERS)
    return StatementFetcher(client, retries=0, sleep=lambda s: None)


def analyse(repo, symbol, stocks, **kw):
    kw.setdefault("fetcher", fetcher())
    return adhoc.analyse_ticker(
        repo,
        SETTINGS,
        symbol,
        fetch=universe_of(stocks),
        pacing=NO_PAUSE,
        sleep=lambda s: None,
        sender=lambda m: None,
        **kw,
    )


def test_normalise_accepts_tickers_only():
    assert adhoc.normalise(" aapl ") == "AAPL" and adhoc.normalise("brk.b") == "BRK.B"
    for bad in ("", "has space", "<script>", "WAYTOOLONGTICKER", "-A"):
        assert adhoc.normalise(bad) is None


def test_a_stock_outside_the_screen_is_analysed_like_any_other(repo):
    # CCC fails the D/E filter, so a scan would never download or analyse it
    out = analyse(repo, "CCC", {"AAA": {}, "CCC": {"debtEquity": 5.0}})
    assert out.status == "ok" and out.summary.startswith("CCC: ok")
    run = repo.get_run(out.run_id)
    assert run["kind"] == "adhoc" and run["status"] == "ok"
    assert repo.latest_statement_fetch("CCC", "income") is not None
    assert repo.latest_statement_fetch("AAA", "income") is None  # only the asked ticker
    assert len(repo.results_for(out.run_id, "CCC")) == 44
    assert {r["kind"] for r in repo.scores_for(out.run_id, "CCC")} >= {"quality", "opportunity"}
    snap = repo.snapshot_for(out.run_id, "CCC")
    assert snap["in_screen"] == 0 and snap["filters_failed"] == 1
    assert repo.get_company("CCC")["name"] == "CCC Corp"


def test_adhoc_runs_never_touch_scans_dashboard_history_or_scheduler(repo):
    scan = run_with(repo, [seed(repo, "AAA")])
    analyse_run(repo, scan)
    repo.finish_run(scan, "ok")
    out = analyse(repo, "CCC", {"CCC": {"debtEquity": 5.0}})
    assert out.status == "ok"
    assert repo.latest_analysed_run()["id"] == scan  # the dashboard still shows the scan
    assert repo.last_successful_run()["id"] == scan
    assert [r["id"] for r in repo.recent_runs()] == [scan]
    assert repo.adhoc_stocks(scan)[0]["symbol"] == "CCC"
    assert repo.exited_stocks(scan) == []  # not an "exited" stock: it was never in the screen
    assert repo.snapshots_for_run(out.run_id)  # but its own snapshot exists
    # the next scan compares against the previous *scan*, never against the ad hoc snapshot
    prev = repo.conn.execute(
        "SELECT MAX(run_id) FROM screener_snapshots WHERE run_id < ? "
        "AND run_id IN (SELECT id FROM runs WHERE kind <> 'adhoc')",
        (out.run_id + 1,),
    ).fetchone()[0]
    assert prev == scan


def test_failed_adhoc_run_does_not_delay_the_next_scheduled_scan(repo):
    from datetime import UTC, datetime

    analyse(repo, "ZZZ", {"AAA": {}})  # unknown ticker -> failed adhoc run
    assert repo.recent_runs(1) == []
    assert is_due(repo, datetime.now(UTC)) is True  # still "no scan yet", not "recently failed"


def test_unknown_ticker_and_missing_statements_fail_with_a_reason(repo):
    out = analyse(repo, "ZZZ", {"AAA": {}})
    assert out.status == "failed" and "unknown ticker" in out.summary
    run = repo.latest_adhoc_run("ZZZ")
    assert run["status"] == "failed" and run["summary"].startswith("ZZZ: unknown")

    out = analyse(repo, "AAA", {"AAA": {}}, fetcher=fetcher(lambda r: httpx.Response(404)))
    assert out.status == "failed" and "no financial statements" in out.summary


def test_block_is_reported_and_alerted(repo):
    def blocked():
        raise Blocked("challenge page")

    out = adhoc.analyse_ticker(
        repo, SETTINGS, "AAA", fetch=blocked, sleep=lambda s: None, sender=lambda m: None
    )
    assert out.status == "blocked"
    assert repo.conn.execute("SELECT kind FROM alerts").fetchone()["kind"] == "blocked"


def test_shares_the_run_lock_with_scans(repo):
    repo.start_run("cli")  # a scan is running
    out = analyse(repo, "AAA", {"AAA": {}})
    assert out.status == "locked" and out.run_id is None


def test_daily_limit(repo):
    for _ in range(adhoc.DAILY_LIMIT):
        repo.finish_run(repo.start_run("adhoc"), "ok", "X: ok")
    assert adhoc.over_daily_limit(repo) is True


# ── API ────────────────────────────────────────────────────────────────────────────────────────
PASSWORD = "correct horse"  # pragma: allowlist secret


@pytest.fixture
def api(tmp_path):
    env = {
        "DASHBOARD_PASSWORD": PASSWORD,
        "SESSION_SECRET": "x" * 32,
        "DB_PATH": str(tmp_path / "t.db"),
    }
    calls = []

    def fake_runner(settings, symbol):
        calls.append(symbol)
        return RunOutcome(None, "ok", "")

    app = create_app(
        load_settings(env), adhoc_runner=fake_runner, profile_starter=lambda s, y, force=False: None
    )
    client = TestClient(app)
    csrf = client.post("/api/auth/login", json={"password": PASSWORD}).json()["csrf"]
    repo = Repository(db.open_database(env["DB_PATH"]))
    return client, csrf, repo, calls


def test_start_analysis_validates_limits_and_starts_a_background_job(api):
    import time

    client, csrf, repo, calls = api
    h = {"x-csrf-token": csrf}
    assert client.post("/api/analyses", json={"symbol": "aapl"}).status_code == 403  # CSRF
    assert client.post("/api/analyses", json={"symbol": "<b>"}, headers=h).status_code == 422
    r = client.post("/api/analyses", json={"symbol": "aapl"}, headers=h)
    assert r.status_code == 202 and r.json() == {"symbol": "AAPL"}
    for _ in range(50):  # the job runs in a thread
        if calls:
            break
        time.sleep(0.02)
    assert calls == ["AAPL"]

    for _ in range(adhoc.DAILY_LIMIT):
        repo.finish_run(repo.start_run("adhoc"), "ok", "X: ok")
    assert client.post("/api/analyses", json={"symbol": "AAPL"}, headers=h).status_code == 429


def test_start_analysis_conflicts_with_a_running_scan(api):
    client, csrf, repo, calls = api
    repo.start_run("cli")
    r = client.post("/api/analyses", json={"symbol": "AAPL"}, headers={"x-csrf-token": csrf})
    assert r.status_code == 409 and calls == []


def test_status_follows_the_run_and_the_stock_page_serves_the_result(api):
    client, csrf, repo, _ = api
    assert client.get("/api/analyses/AAPL").json()["status"] == "none"
    run = repo.start_run("adhoc")
    repo.set_run_summary(run, "AAPL")
    status = client.get("/api/analyses/aapl").json()
    assert status["status"] == "running" and status["analyses_left_today"] == adhoc.DAILY_LIMIT - 1
    repo.finish_run(run, "failed", "AAPL: unknown ticker (not in the StockAnalysis screener)")
    status = client.get("/api/analyses/AAPL").json()
    assert status["status"] == "failed" and status["message"].startswith("unknown ticker")

    # an analysed stock outside the screen: detail page + the dashboard's separate list
    scan = run_with(repo, [seed(repo, "AAA")])
    analyse_run(repo, scan)
    repo.finish_run(scan, "ok")
    out = analyse(repo, "CCC", {"CCC": {"debtEquity": 5.0}})
    assert out.status == "ok"
    detail = client.get("/api/stocks/CCC").json()
    assert detail["adhoc"] is True and detail["in_latest_run"] is False and detail["criteria"]
    assert client.get("/api/stocks/AAA").json()["adhoc"] is False
    listing = client.get("/api/stocks").json()
    assert [s["symbol"] for s in listing["adhoc"]] == ["CCC"] and listing["exited"] == []
    assert [s["symbol"] for s in listing["stocks"]] == ["AAA"]


def test_profile_button_needs_configuration(api):
    client, csrf, _, _ = api
    r = client.post("/api/profiles/AAPL", headers={"x-csrf-token": csrf})
    assert r.status_code == 503  # no GOOGLE_API_KEY / MY_EMAIL in this app's settings


def test_profile_job_reports_unsupported_and_conflicts_while_running(tmp_path):
    import threading

    from value_scanner.jobs import profiles as pj

    env = {"DB_PATH": str(tmp_path / "p.db"), "GOOGLE_API_KEY": "k" * 10, "MY_EMAIL": "me@e.com"}
    settings = load_settings(env)
    db.open_database(env["DB_PATH"]).close()
    assert pj.profile_job_status("KGC") == "none"

    gate = threading.Event()

    def slow_refresh(repo, settings, symbol, sec, generate=None, force=False):
        gate.wait(5)
        return "unsupported"

    original = pj.refresh_profile, pj.SecClient
    pj.refresh_profile, pj.SecClient = slow_refresh, lambda contact: None
    try:
        assert pj.start_profile(settings, "KGC") is True
        assert pj.profile_job_status("KGC") == "running"
        assert pj.start_profile(settings, "KGC") is False  # one at a time per stock
        gate.set()
        for _ in range(100):
            if pj.profile_job_status("KGC") != "running":
                break
            threading.Event().wait(0.02)
        assert pj.profile_job_status("KGC") == "unsupported"
    finally:
        pj.refresh_profile, pj.SecClient = original


def test_profile_status_endpoint(api):
    client, csrf, _, _ = api
    assert client.get("/api/profiles/QQQQ/status").json() == {
        "symbol": "QQQQ",
        "status": "none",
        "text": "",
    }


def test_reanalysis_with_unchanged_reports_downloads_nothing_and_only_updates_the_price(repo):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200, text=statement_html())

    first = analyse(repo, "CCC", {"CCC": {"price": 50.0}}, fetcher=fetcher(handler))
    # income, balance sheet, cash flow, quarterly income
    assert first.status == "ok" and len(requests) == 4

    second = analyse(
        repo, "CCC", {"CCC": {"price": 61.5, "pbRatio": 4.0}}, fetcher=fetcher(handler)
    )
    assert second.status == "ok"
    assert len(requests) == 4  # the reports are fresh: not one more statement request
    assert repo.snapshot_for(first.run_id, "CCC")["price"] == 50.0
    new = repo.snapshot_for(second.run_id, "CCC")
    assert new["price"] == 61.5 and new["pb_ratio"] == 4.0  # price and multiples are current
    # and the criteria were re-evaluated against the new multiples
    assert len(repo.results_for(second.run_id, "CCC")) == 44


def test_a_new_report_date_since_the_last_download_is_downloaded_again(repo):
    """R5: the screener now shows a newer `lastReportDate` than the one stored with the download."""
    requests = []

    def handler(request):
        requests.append(1)
        return httpx.Response(200, text=statement_html())

    analyse(repo, "CCC", {"CCC": {"lastReportDate": "2026-06-30"}}, fetcher=fetcher(handler))
    first = len(requests)
    analyse(repo, "CCC", {"CCC": {"lastReportDate": "2026-06-30"}}, fetcher=fetcher(handler))
    assert len(requests) == first  # same report date: nothing to download
    analyse(repo, "CCC", {"CCC": {"lastReportDate": "2026-09-30"}}, fetcher=fetcher(handler))
    assert len(requests) > first


def test_without_a_report_date_a_new_report_is_still_found_by_the_earnings_date(repo):
    """D18 fallback: when the screener gives no `lastReportDate`, the earnings-date rules apply."""
    requests = []

    def handler(request):
        requests.append(1)
        return httpx.Response(200, text=statement_html())

    no_date = {"lastReportDate": None}
    first_stock = {"CCC": {**no_date, "lastEarningsDate": "2026-08-01"}}
    analyse(repo, "CCC", first_stock, fetcher=fetcher(handler))
    first = len(requests)
    # the company reported again after our download (D18: try again 1 day after the report)
    repo.conn.execute("UPDATE statement_fetches SET fetched_at = '2026-08-02T00:00:00Z'")
    reported_again = {"CCC": {**no_date, "lastEarningsDate": "2026-11-05"}}
    analyse(repo, "CCC", reported_again, fetcher=fetcher(handler))
    assert len(requests) > first


def test_recent_universe_is_fetched_without_a_pause_and_reused_for_a_short_while(monkeypatch):
    from value_scanner.jobs import adhoc

    calls = []
    clock = {"t": 1000.0}
    monkeypatch.setattr(adhoc, "_universe_cache", None)
    monkeypatch.setattr(adhoc.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(adhoc, "fetch_universe", lambda pause=4.0: calls.append(pause) or object())
    first = adhoc._recent_universe()
    clock["t"] += adhoc.UNIVERSE_TTL - 1
    assert adhoc._recent_universe() is first and calls == [0.0]  # no pause, one fetch
    clock["t"] += 2
    assert adhoc._recent_universe() is not first and calls == [0.0, 0.0]  # expired -> fetched again


def test_a_blocked_universe_fetch_is_not_cached(monkeypatch):
    from value_scanner.jobs import adhoc
    from value_scanner.sources.screener import Blocked

    state = {"fail": True, "calls": 0}

    def fetch(pause=4.0):
        state["calls"] += 1
        if state["fail"]:
            raise Blocked("HTTP 429")
        return object()

    monkeypatch.setattr(adhoc, "_universe_cache", None)
    monkeypatch.setattr(adhoc, "fetch_universe", fetch)
    with pytest.raises(Blocked):
        adhoc._recent_universe()
    state["fail"] = False
    adhoc._recent_universe()
    assert state["calls"] == 2
