import httpx
import pytest

from tests.factories import screener_json, statement_html
from value_scanner.jobs.alerts import build_message, send_pending_alerts
from value_scanner.jobs.pipeline import run_scan
from value_scanner.jobs.refresh import Pacing
from value_scanner.settings import load_settings
from value_scanner.sources.screener import Blocked, StructureChanged, parse_universe
from value_scanner.sources.stockanalysis import HEADERS, StatementFetcher
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

SETTINGS = load_settings(
    {"MY_EMAIL": "me@example.com", "SMTP_HOST": "smtp.example.com", "SMTP_USER": "bot@example.com"}
)
NO_PAUSE = Pacing(pause=(0, 0), rest_every=(1000, 1000), rest=(0, 0), block_wait=0)


@pytest.fixture
def repo():
    return Repository(db.open_database(":memory:"))


def universe_of(stocks):
    return lambda: parse_universe(*screener_json(stocks))


def fetcher(handler=None):
    handler = handler or (lambda r: httpx.Response(200, text=statement_html()))
    client = httpx.Client(transport=httpx.MockTransport(handler), headers=HEADERS)
    return StatementFetcher(client, retries=0, sleep=lambda s: None)


class Outbox(list):
    def __call__(self, message):
        self.append(message)


def scan(repo, stocks, outbox=None, **kw):
    kw.setdefault("fetcher", fetcher())
    kw.setdefault("pacing", NO_PAUSE)
    return run_scan(
        repo,
        SETTINGS,
        fetch=universe_of(stocks),
        sleep=lambda s: None,
        sender=outbox if outbox is not None else Outbox(),
        log=lambda m: None,
        **kw,
    )


def test_successful_run_end_to_end(repo):
    out = scan(repo, {"AAA": {}, "BBB": {}, "CCC": {"debtEquity": 5.0}})
    assert out.status == "ok" and "2 in screen" in out.summary
    run = repo.get_run(out.run_id)
    assert (
        run["status"] == "ok"
        and run["finished_at"]
        and (run["progress_done"], run["progress_total"]) == (6, 6)
    )  # downloads
    assert repo.latest_statement_fetch("AAA", "income")
    assert repo.latest_statement_fetch("CCC", "income") is None  # not in the screen
    assert repo.last_successful_run()["id"] == out.run_id
    assert any("finished: ok" in r["message"] for r in repo.run_log(out.run_id))


def test_second_run_downloads_nothing_new(repo):
    scan(repo, {"AAA": {}})
    out = scan(repo, {"AAA": {}})
    assert out.status == "ok" and "fresh-skipped=3" in out.summary and "ok=0" in out.summary


def test_limit_restricts_downloads(repo):
    out = scan(repo, {"AAA": {}, "BBB": {}}, limit=1)
    assert "ok=3" in out.summary  # 1 stock x 3 statements
    assert repo.latest_statement_fetch("BBB", "income") is None


def test_second_run_is_locked_while_first_runs(repo):
    repo.start_run("scheduled")
    out = scan(repo, {"AAA": {}})
    assert out.status == "locked" and out.run_id is None


def test_blocked_screener_ends_run_and_alerts_once(repo):
    def fetch():
        raise Blocked("HTTP 403")

    outbox = Outbox()
    out = run_scan(
        repo, SETTINGS, fetch=fetch, sender=outbox, sleep=lambda s: None, log=lambda m: None
    )
    assert out.status == "blocked"
    assert repo.get_run(out.run_id)["status"] == "blocked"
    assert len(outbox) == 1 and "blocked" in outbox[0]["Subject"].lower()


def test_blocked_downloads_alert_and_stop(repo):
    f = fetcher(lambda r: httpx.Response(429, text="slow"))
    outbox = Outbox()
    out = scan(
        repo,
        {"AAA": {}},
        outbox,
        fetcher=f,
        pacing=Pacing(pause=(0, 0), block_wait=0, max_blocks_in_a_row=2),
    )
    assert out.status == "blocked"
    kinds = [a["kind"] for a in repo.conn.execute("SELECT kind FROM alerts")]
    assert kinds == ["blocked"] and len(outbox) == 1


def test_structure_change_fails_run_with_alert(repo):
    def fetch():
        raise StructureChanged("fields gone")

    outbox = Outbox()
    out = run_scan(
        repo, SETTINGS, fetch=fetch, sender=outbox, sleep=lambda s: None, log=lambda m: None
    )
    assert out.status == "failed" and len(outbox) == 1
    assert "structure" in outbox[0]["Subject"].lower() or "shape" in outbox[0]["Subject"].lower()


def test_many_failed_downloads_send_alert_but_run_is_ok(repo):
    f = fetcher(lambda r: httpx.Response(404, text="gone"))
    outbox = Outbox()
    out = scan(repo, {"AAA": {}, "BBB": {}}, outbox, fetcher=f)
    assert out.status == "ok" and "failed=6" in out.summary
    assert len(outbox) == 1 and "failed" in outbox[0]["Subject"].lower()


def test_unexpected_error_marks_run_failed(repo):
    def fetch():
        raise RuntimeError("boom")

    outbox = Outbox()
    out = run_scan(
        repo, SETTINGS, fetch=fetch, sender=outbox, sleep=lambda s: None, log=lambda m: None
    )
    assert out.status == "failed" and repo.get_run(out.run_id)["error"] == "RuntimeError: boom"
    assert len(outbox) == 1


def test_keyboard_interrupt_leaves_interrupted_not_running(repo):
    def fetch():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_scan(
            repo, SETTINGS, fetch=fetch, sender=Outbox(), sleep=lambda s: None, log=lambda m: None
        )
    assert repo.conn.execute("SELECT status FROM runs").fetchone()[0] == "interrupted"
    repo.start_run("cli")  # the lock was released


# ── alerts ───────────────────────────────────────────────────────────────────────────────────
def test_alert_message_goes_to_my_email_without_leaking_it_elsewhere():
    msg = build_message(SETTINGS, "Subject", "Body")
    assert msg["To"] == "me@example.com" and msg["From"] == "bot@example.com"
    assert "me@example.com" not in msg["Subject"] and "me@example.com" not in msg.get_content()


def test_send_failure_is_recorded_and_retried(repo):
    repo.add_alert("blocked", "S", "B")

    def broken(message):
        raise OSError("smtp down")

    assert send_pending_alerts(repo, SETTINGS, broken) == (0, 1)
    row = repo.conn.execute("SELECT * FROM alerts").fetchone()
    assert row["sent_at"] is None and "smtp down" in row["error"]
    outbox = Outbox()
    assert send_pending_alerts(repo, SETTINGS, outbox) == (1, 0)
    assert repo.conn.execute("SELECT sent_at, error FROM alerts").fetchone()[1] is None


def test_without_smtp_alerts_stay_in_db(repo):
    repo.add_alert("blocked", "S", "B")
    assert send_pending_alerts(repo, load_settings({})) == (0, 1)
    assert "not configured" in repo.conn.execute("SELECT error FROM alerts").fetchone()[0]
