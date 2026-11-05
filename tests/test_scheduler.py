import threading
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from value_scanner.api.app import create_app
from value_scanner.jobs.pipeline import RunOutcome
from value_scanner.jobs.scheduler import RETRY_AFTER, is_due, run_now, tick
from value_scanner.settings import load_settings
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

T0 = datetime(2026, 6, 1, 12, tzinfo=UTC)
TEST_PASSWORD = "pw-for-tests"  # pragma: allowlist secret
TEST_SECRET = "s" * 32


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def repo(clock):
    return Repository(db.open_database(":memory:"), clock)


def finish(repo, clock, status="ok"):
    run = repo.start_run("scheduled")
    repo.finish_run(run, status)
    return run


def test_first_run_is_due_immediately(repo):
    assert is_due(repo, T0)


def test_due_after_n_days_since_last_success(repo, clock):
    finish(repo, clock)
    assert not is_due(repo, T0 + timedelta(days=6, hours=23))
    assert is_due(repo, T0 + timedelta(days=7))


def test_days_setting_is_respected(repo, clock):
    finish(repo, clock)
    repo.set_setting("days_between_runs", "2")
    assert not is_due(repo, T0 + timedelta(days=1, hours=23))
    assert is_due(repo, T0 + timedelta(days=2))


def test_never_due_while_a_run_is_running(repo, clock):
    repo.start_run("manual")
    assert not is_due(repo, T0 + timedelta(days=100))


@pytest.mark.parametrize("status", ["failed", "blocked", "interrupted"])
def test_waits_after_a_failed_run_before_retrying(repo, clock, status):
    finish(repo, clock, status)
    assert not is_due(repo, T0 + RETRY_AFTER - timedelta(minutes=1))
    assert is_due(repo, T0 + RETRY_AFTER + timedelta(minutes=1))


def test_failed_run_does_not_reset_the_success_clock(repo, clock):
    finish(repo, clock, "ok")
    clock.t = T0 + timedelta(days=5)
    finish(repo, clock, "failed")
    assert is_due(repo, T0 + timedelta(days=8))  # 8 days since the success, 3 since the failure


# ── tick / run now / API ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def env(tmp_path):
    return {
        "DASHBOARD_PASSWORD": TEST_PASSWORD,
        "SESSION_SECRET": TEST_SECRET,  # pragma: allowlist secret
        "DB_PATH": str(tmp_path / "t.db"),
    }


def test_tick_runs_only_when_due(env):
    settings = load_settings(env)
    calls = []

    def runner(s, kind):
        calls.append(kind)
        return RunOutcome(1, "ok", "")

    assert tick(settings, runner, now=lambda: T0) is not None and calls == ["scheduled"]
    conn = db.open_database(env["DB_PATH"])
    repo = Repository(conn, lambda: T0)
    repo.finish_run(repo.start_run("scheduled"), "ok")
    conn.close()
    assert tick(settings, runner, now=lambda: T0 + timedelta(days=1)) is None
    assert calls == ["scheduled"]


def test_run_now_starts_a_thread_and_refuses_when_running(env):
    settings = load_settings(env)
    db.open_database(env["DB_PATH"]).close()
    started = threading.Event()
    kinds = []

    def runner(s, kind):
        kinds.append(kind)
        started.set()
        return RunOutcome(1, "ok", "")

    assert run_now(settings, runner) is True
    assert started.wait(2) and kinds == ["manual"]

    conn = db.connect(env["DB_PATH"])
    Repository(conn).start_run("scheduled")
    conn.close()
    assert run_now(settings, runner) is False


def test_api_run_now_needs_login_and_csrf_and_returns_409_when_busy(env):
    started = threading.Event()
    app = create_app(
        load_settings(env), runner=lambda s, k: (started.set(), RunOutcome(1, "ok", ""))[1]
    )
    client = TestClient(app)
    assert client.post("/api/runs").status_code == 401
    csrf = client.post("/api/auth/login", json={"password": TEST_PASSWORD}).json()[
        "csrf"
    ]  # pragma: allowlist secret
    assert client.post("/api/runs").status_code == 403
    assert client.post("/api/runs", headers={"x-csrf-token": csrf}).status_code == 202
    assert started.wait(2)

    conn = db.connect(env["DB_PATH"])
    Repository(conn).start_run("manual")
    conn.close()
    assert client.post("/api/runs", headers={"x-csrf-token": csrf}).status_code == 409
