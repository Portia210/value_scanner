import pytest
from fastapi.testclient import TestClient

from tests.test_analyze import run_with, seed
from value_scanner.api import security
from value_scanner.api.app import create_app
from value_scanner.jobs.analyze import analyse_run
from value_scanner.settings import load_settings
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

PASSWORD = "correct horse"  # pragma: allowlist secret
ENV = {"DASHBOARD_PASSWORD": PASSWORD, "SESSION_SECRET": "x" * 32}


@pytest.fixture
def env(tmp_path):
    return {**ENV, "DB_PATH": str(tmp_path / "t.db")}


@pytest.fixture
def repo(env):
    r = Repository(db.open_database(env["DB_PATH"]))
    yield r
    r.conn.close()


@pytest.fixture
def client(env, repo):
    return TestClient(create_app(load_settings(env)))


def login(client):
    r = client.post("/api/auth/login", json={"password": PASSWORD})
    assert r.status_code == 200
    return r.json()["csrf"]


def test_password_without_secret_refuses_to_start(env):
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app(load_settings({"DB_PATH": env["DB_PATH"], "DASHBOARD_PASSWORD": PASSWORD}))


@pytest.fixture
def local_client(env):
    return TestClient(
        create_app(load_settings({"DB_PATH": env["DB_PATH"]})), base_url="http://localhost"
    )


def test_local_mode_needs_no_login(local_client):
    assert local_client.get("/api/runs").status_code == 200
    assert local_client.get("/api/settings").json() == {"days_between_runs": 7}
    csrf = local_client.get("/api/auth/me").json()["csrf"]
    body = {"days_between_runs": 4}
    assert local_client.put("/api/settings", json=body).status_code == 403  # header still needed
    assert (
        local_client.put("/api/settings", json=body, headers={"x-csrf-token": csrf}).status_code
        == 200
    )
    any_password = {"password": "anything"}  # pragma: allowlist secret
    assert local_client.post("/api/auth/login", json=any_password).status_code == 200


@pytest.mark.parametrize("host", ["evil.example.com", "192.168.1.5:8000", "localhost.evil.com"])
def test_local_mode_rejects_other_host_headers(local_client, host):
    assert local_client.get("/api/runs", headers={"host": host}).status_code == 403


@pytest.mark.parametrize("host", ["localhost", "localhost:8000", "127.0.0.1:8000", "[::1]:8000"])
def test_local_mode_accepts_loopback_hosts(local_client, host):
    assert local_client.get("/api/health", headers={"host": host}).status_code == 200


def test_cli_refuses_open_dashboard_on_public_interface(monkeypatch, tmp_path):
    from value_scanner.cli import main

    monkeypatch.setenv("DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)  # never read the real .env
    with pytest.raises(SystemExit) as exc:
        main(["serve", "--host", "0.0.0.0"])
    assert exc.value.code == 2


def test_health_is_public_and_everything_else_needs_login(client):
    assert client.get("/api/health").json() == {"ok": True}
    for path in (
        "/api/stocks",
        "/api/stocks/AAA",
        "/api/runs",
        "/api/runs/1/log",
        "/api/settings",
        "/api/auth/me",
    ):
        assert client.get(path).status_code == 401, path


def test_wrong_password_and_rate_limit(client):
    wrong = {"password": "wrong-on-purpose"}  # pragma: allowlist secret
    for _ in range(security.MAX_FAILED_LOGINS):
        assert client.post("/api/auth/login", json=wrong).status_code == 401
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 429


def test_login_sets_a_hardened_cookie(client):
    r = client.post("/api/auth/login", json={"password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/auth/me").json()["csrf"] == r.json()["csrf"]


def test_secure_flag_behind_https_proxy(client):
    r = client.post(
        "/api/auth/login", json={"password": PASSWORD}, headers={"x-forwarded-proto": "https"}
    )
    assert "secure" in r.headers["set-cookie"].lower()


def test_tampered_cookie_is_rejected(client):
    login(client)
    client.cookies.set(security.SESSION_COOKIE, "garbage")
    assert client.get("/api/auth/me").status_code == 401


def test_post_needs_csrf_header(client):
    csrf = login(client)
    body = {"days_between_runs": 3}
    assert client.put("/api/settings", json=body).status_code == 403
    assert (
        client.put("/api/settings", json=body, headers={"x-csrf-token": "bad"}).status_code == 403
    )
    assert client.put("/api/settings", json=body, headers={"x-csrf-token": csrf}).status_code == 200
    assert client.get("/api/settings").json() == {"days_between_runs": 3}


def test_settings_default_and_validation(client):
    csrf = login(client)
    assert client.get("/api/settings").json() == {"days_between_runs": 7}
    for bad in (0, 61, "x"):
        r = client.put(
            "/api/settings", json={"days_between_runs": bad}, headers={"x-csrf-token": csrf}
        )
        assert r.status_code == 422


def test_logout_clears_session(client):
    csrf = login(client)
    assert client.post("/api/auth/logout", headers={"x-csrf-token": csrf}).status_code == 200
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_security_headers_on_every_response(client):
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_stock_endpoints_before_and_after_a_run(client, repo):
    login(client)
    assert client.get("/api/stocks").json() == {"run": None, "stocks": []}
    assert client.get("/api/stocks/AAA").status_code == 404

    run = run_with(
        repo, [seed(repo, "AAA"), seed(repo, "BBB", pe_ratio=40.0, pb_ratio=8.0, ps_ratio=6.0)]
    )
    analyse_run(repo, run)
    repo.finish_run(run, "ok")

    data = client.get("/api/stocks").json()
    assert data["run"]["id"] == run and [s["symbol"] for s in data["stocks"]] == ["AAA", "BBB"]
    aaa = data["stocks"][0]
    assert set(aaa["scores"]) == {
        "screen",
        "graham",
        "fisher",
        "piotroski",
        "quality",
        "opportunity",
    }
    assert aaa["labels"] == ["regular"] and isinstance(aaa["candidate"], bool)

    detail = client.get("/api/stocks/aaa").json()  # symbol is case-insensitive
    assert len(detail["results"]) == 28 and detail["company"]["symbol"] == "AAA"
    assert set(detail["components"]) == {"graham_number", "fair_pe", "vs_history", "price_sales"}
    assert detail["history"]["quality"][0]["run_id"] == run
    assert client.get("/api/stocks/ZZZ").status_code == 404


def test_runs_and_log(client, repo):
    login(client)
    run = repo.start_run("cli")
    repo.log(run, "info", "hello")
    repo.finish_run(run, "ok", summary="done")
    runs = client.get("/api/runs").json()
    assert runs[0]["id"] == run and runs[0]["status"] == "ok"
    assert client.get(f"/api/runs/{run}/log").json()[0]["message"] == "hello"
    assert client.get("/api/runs/999/log").status_code == 404
