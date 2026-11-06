import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from value_scanner.storage import db
from value_scanner.storage.repo import (
    STATEMENT_FETCHES_KEPT,
    Repository,
    RunAlreadyRunning,
)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def repo(clock):
    conn = db.open_database(":memory:")
    repo = Repository(conn, clock)
    repo.upsert_company("AAA", name="Aaa Inc", sector="Technology")
    return repo


# ── migrations ──────────────────────────────────────────────────────────────────────────────
def test_migrate_is_idempotent_and_versioned():
    conn = db.connect(":memory:")
    assert db.schema_version(conn) == 0
    v = db.migrate(conn)
    assert v >= 1
    assert db.migrate(conn) == v
    assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == v


def test_all_planned_tables_exist():
    conn = db.open_database(":memory:")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {
        "settings",
        "runs",
        "run_log",
        "alerts",
        "parse_failures",
        "companies",
        "screener_snapshots",
        "statement_fetches",
        "statement_values",
        "classifications",
        "results",
        "scores",
        "score_components",
        "membership_events",
        "profiles",
    }
    assert expected <= names


def test_file_database_uses_wal(tmp_path):
    conn = db.open_database(tmp_path / "sub" / "x.db")
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# ── settings ────────────────────────────────────────────────────────────────────────────────
def test_settings_roundtrip_and_overwrite(repo):
    assert repo.get_setting("days") is None
    assert repo.get_setting("days", "7") == "7"
    repo.set_setting("days", "3")
    repo.set_setting("days", "5")
    assert repo.get_setting("days") == "5"


# ── runs and the lock ───────────────────────────────────────────────────────────────────────
def test_only_one_run_can_be_running(repo):
    first = repo.start_run("manual")
    with pytest.raises(RunAlreadyRunning):
        repo.start_run("scheduled")
    repo.finish_run(first, "ok", summary="done")
    assert repo.start_run("scheduled") > first  # lock released


def test_finish_requires_final_status(repo):
    run = repo.start_run("cli")
    with pytest.raises(ValueError):
        repo.finish_run(run, "running")


def test_interrupted_run_is_marked_at_startup(repo):
    run = repo.start_run("cli")
    assert repo.mark_interrupted_runs() == 1
    assert repo.get_run(run)["status"] == "interrupted"
    repo.start_run("cli")  # lock is free again


def test_last_successful_run_ignores_failed(repo, clock):
    a = repo.start_run("cli")
    repo.finish_run(a, "ok")
    clock.advance(hours=1)
    b = repo.start_run("cli")
    repo.finish_run(b, "failed", error="boom")
    assert repo.last_successful_run()["id"] == a


def test_progress_and_log(repo):
    run = repo.start_run("manual")
    repo.update_progress(run, 3, 10)
    repo.log(run, "info", "one")
    repo.log(run, "error", "two")
    row = repo.get_run(run)
    assert (row["progress_done"], row["progress_total"]) == (3, 10)
    assert [r["message"] for r in repo.run_log(run)] == ["one", "two"]


def test_invalid_status_rejected(repo):
    with pytest.raises(sqlite3.IntegrityError):
        repo.conn.execute("INSERT INTO runs (kind, status, started_at) VALUES ('cli','weird','x')")


# ── companies, snapshots, membership ────────────────────────────────────────────────────────
def test_upsert_company_keeps_existing_values_on_none(repo, clock):
    first = repo.get_company("AAA")["first_seen_at"]
    clock.advance(days=1)
    repo.upsert_company("AAA", industry="Software")
    row = repo.get_company("AAA")
    assert row["sector"] == "Technology" and row["industry"] == "Software"
    assert row["first_seen_at"] == first and row["last_seen_at"] > first


def test_snapshot_roundtrip_and_unknown_field(repo):
    run = repo.start_run("cli")
    repo.save_snapshot(run, "AAA", {"in_screen": 1, "price": 10.5, "debt_equity": 0.2})
    row = repo.snapshots_for_run(run)["AAA"]
    assert row["price"] == 10.5 and row["pe_ratio"] is None
    with pytest.raises(ValueError):
        repo.save_snapshot(run, "AAA", {"nonsense": 1})
    with pytest.raises(sqlite3.IntegrityError):  # one row per run and symbol
        repo.save_snapshot(run, "AAA", {"in_screen": 0})


def test_snapshot_requires_known_company(repo):
    run = repo.start_run("cli")
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_snapshot(run, "ZZZ", {"in_screen": 1})


def test_membership_events(repo):
    run = repo.start_run("cli")
    repo.add_membership_event(
        run, "AAA", "exit", "price", {"filter": "peRatio", "before": 6, "after": 4}
    )
    ev = repo.membership_events("AAA")[0]
    assert ev["direction"] == "exit" and '"peRatio"' in ev["detail"]
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_membership_event(run, "AAA", "exit", "because", None)


# ── statements ──────────────────────────────────────────────────────────────────────────────
def test_statement_fetch_keeps_only_last_four_good(repo, clock):
    ids = []
    for i in range(6):
        clock.advance(days=1)
        ids.append(
            repo.save_statement_fetch(
                "AAA",
                "income",
                "stockanalysis",
                "ok",
                values=[("Revenue", "FY 2025", 100.0 + i), ("Net Income", "FY 2025", None)],
                latest_period="FY 2025",
            )
        )
    left = repo.conn.execute(
        "SELECT id FROM statement_fetches WHERE symbol='AAA' AND statement='income' ORDER BY id"
    ).fetchall()
    assert [r["id"] for r in left] == ids[-STATEMENT_FETCHES_KEPT:]
    # cascade removed the values of pruned fetches
    assert (
        repo.conn.execute("SELECT COUNT(DISTINCT fetch_id) FROM statement_values").fetchone()[0]
        == 4
    )
    latest = repo.latest_statement_fetch("AAA", "income")
    assert latest["id"] == ids[-1]
    vals = {(r["item"], r["period"]): r["value"] for r in repo.statement_values(latest["id"])}
    assert vals[("Revenue", "FY 2025")] == 105.0 and vals[("Net Income", "FY 2025")] is None


def test_failed_fetch_does_not_evict_good_ones_or_count_as_latest(repo, clock):
    good = repo.save_statement_fetch("AAA", "income", "sa", "ok", [("Revenue", "FY 2025", 1.0)])
    for _ in range(6):
        clock.advance(hours=1)
        repo.save_statement_fetch("AAA", "income", "sa", "blocked")
    assert repo.latest_statement_fetch("AAA", "income")["id"] == good


def test_statements_are_kept_per_symbol_and_statement(repo):
    repo.upsert_company("BBB")
    for sym in ("AAA", "BBB"):
        for st in ("income", "balance_sheet"):
            for _ in range(5):
                repo.save_statement_fetch(sym, st, "sa", "ok")
    n = repo.conn.execute("SELECT COUNT(*) FROM statement_fetches").fetchone()[0]
    assert n == 4 * STATEMENT_FETCHES_KEPT


# ── results and scores ──────────────────────────────────────────────────────────────────────
def test_results_and_na_are_stored_as_na(repo):
    run = repo.start_run("cli")
    repo.save_results(
        run,
        "AAA",
        [
            {
                "guru": "graham",
                "criterion_id": "g1",
                "status": "PASS",
                "value": 3.0,
                "threshold": 2.0,
                "strength": 0.75,
            },
            {"guru": "graham", "criterion_id": "g2", "status": "NA", "note": "no data"},
        ],
    )
    rows = {r["criterion_id"]: r for r in repo.results_for(run, "AAA")}
    assert rows["g2"]["status"] == "NA" and rows["g2"]["value"] is None
    assert rows["g1"]["strength"] == 0.75


def test_results_reject_bad_status_and_strength(repo):
    run = repo.start_run("cli")
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_results(run, "AAA", [{"guru": "graham", "criterion_id": "x", "status": "OK"}])
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_results(
            run, "AAA", [{"guru": "graham", "criterion_id": "y", "status": "PASS", "strength": 1.5}]
        )


def test_score_history_across_runs_with_components(repo, clock):
    for score in (0.5, 0.6):
        clock.advance(days=1)
        run = repo.start_run("cli")
        repo.save_score(
            run,
            "AAA",
            "opportunity",
            score,
            0.8,
            components={"graham_number": score, "fair_pe": None},
        )
        repo.finish_run(run, "ok")
    hist = repo.score_history("AAA", "opportunity")
    assert [h["score"] for h in hist] == [0.5, 0.6]
    n = repo.conn.execute(
        "SELECT COUNT(*) FROM score_components WHERE component='fair_pe'"
    ).fetchone()[0]
    assert n == 2


def test_classification_and_profile(repo):
    run = repo.start_run("cli")
    repo.save_classification(run, "AAA", {"tech": "sector=Technology", "growth": None})
    assert repo.conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0] == 2
    repo.save_profile("AAA", "old", "0001", "gemini", "v1", filing_date="2025-02-01")
    repo.save_profile("AAA", "new", "0002", "gemini", "v1", filing_date="2026-02-01")
    repo.save_profile("AAA", "new2", "0002", "gemini", "v1", filing_date="2026-02-01")  # upsert
    assert repo.latest_profile("AAA")["text"] == "new2"
    assert repo.conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 2


# ── retention ───────────────────────────────────────────────────────────────────────────────
def test_retention_windows(repo, clock):
    run = repo.start_run("cli")
    repo.log(run, "info", "old")
    repo.save_snapshot(run, "AAA", {"in_screen": 1})
    repo.save_statement_fetch("AAA", "income", "sa", "blocked")
    clock.advance(days=89)
    repo.log(run, "info", "recent")
    assert repo.apply_retention() == {"run_log": 0, "screener_snapshots": 0, "statement_fetches": 0}
    clock.advance(days=2)  # 91 days after the first rows
    deleted = repo.apply_retention()
    assert deleted["run_log"] == 1 and deleted["statement_fetches"] == 1
    assert deleted["screener_snapshots"] == 0
    assert [r["message"] for r in repo.run_log(run)] == ["recent"]
    clock.advance(days=310)  # > 400 days since the snapshot
    assert repo.apply_retention()["screener_snapshots"] == 1


def test_alerts_and_parse_failures(repo):
    aid = repo.add_alert("blocked", "Blocked", "Cloudflare challenge")
    repo.mark_alert_sent(aid)
    row = repo.conn.execute("SELECT * FROM alerts WHERE id=?", (aid,)).fetchone()
    assert row["sent_at"] is not None and row["error"] is None
    repo.mark_alert_sent(aid, error="smtp down")
    row = repo.conn.execute("SELECT * FROM alerts WHERE id=?", (aid,)).fetchone()
    assert row["sent_at"] is None and row["error"] == "smtp down"
    repo.add_parse_failure("stockanalysis", "no_table", "x" * 5000, symbol="AAA")
    assert len(repo.conn.execute("SELECT sample FROM parse_failures").fetchone()[0]) == 2000


def test_transaction_rolls_back_on_error(repo):
    with pytest.raises(RuntimeError), repo.transaction():
        repo.set_setting("k", "v")
        raise RuntimeError("fail")
    assert repo.get_setting("k") is None


def _v1_database_with_children(path):
    """A database as it was before migration 0002, with rows that reference `runs`."""
    conn = db.connect(path)
    conn.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    first = db._KNOWN_MIGRATIONS[0][1]
    conn.execute("BEGIN")
    for stmt in db._split_statements(first):
        conn.execute(stmt)
    conn.execute("INSERT INTO schema_migrations VALUES (1, 'x')")
    conn.execute("COMMIT")
    conn.execute("INSERT INTO runs (kind, status, started_at) VALUES ('cli', 'ok', 'x')")
    conn.execute("INSERT INTO companies (symbol, first_seen_at, last_seen_at) VALUES ('A','x','x')")
    conn.execute("INSERT INTO run_log (run_id, ts, level, message) VALUES (1, 'x', 'info', 'm')")
    conn.execute("INSERT INTO scores (run_id, symbol, kind, score) VALUES (1, 'A', 'quality', .5)")
    conn.execute(
        "INSERT INTO membership_events (run_id, symbol, direction, reason_type, created_at)"
        " VALUES (1, 'A', 'exit', 'price', 'x')"
    )
    conn.close()


def test_table_rebuild_migration_keeps_every_row_that_references_runs(tmp_path):
    """Regression (2026-11-06): migration 0002 rebuilds `runs`; the cascade must not fire."""
    path = tmp_path / "old.db"
    _v1_database_with_children(path)
    conn = db.open_database(path)
    assert db.schema_version(conn) >= 2
    for table in ("runs", "run_log", "scores", "membership_events"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1, table
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1  # switched back on
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.execute("INSERT INTO runs (kind, status, started_at) VALUES ('adhoc', 'ok', 'x')")


def test_old_code_refuses_a_newer_database_and_never_applies_migrations_added_later(
    tmp_path, monkeypatch
):
    path = tmp_path / "new.db"
    db.open_database(path).close()  # fully migrated by current code
    monkeypatch.setattr(db, "_KNOWN_MIGRATIONS", db._KNOWN_MIGRATIONS[:1])  # an "older process"
    with pytest.raises(db.SchemaTooNew):
        db.open_database(path)
    # and an older process on an older database applies only what it knew at start
    old = tmp_path / "old.db"
    _v1_database_with_children(old)
    conn = db.open_database(old)
    assert db.schema_version(conn) == 1


def test_report_date_migration_is_additive_and_keeps_every_row(tmp_path):
    """Migration 0003 (R5) only adds columns: existing rows stay, the new columns are NULL."""
    path = tmp_path / "v2.db"
    conn = db.connect(path)
    conn.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    for version, statements in db._KNOWN_MIGRATIONS[:2]:
        db._apply(conn, version, statements, verify_foreign_keys=version == 2)
    conn.execute("INSERT INTO runs (kind, status, started_at) VALUES ('cli', 'ok', 'x')")
    conn.execute("INSERT INTO companies (symbol, first_seen_at, last_seen_at) VALUES ('A','x','x')")
    conn.execute(
        "INSERT INTO screener_snapshots (run_id, symbol, captured_at, in_screen) "
        "VALUES (1, 'A', 'x', 1)"
    )
    conn.execute(
        "INSERT INTO statement_fetches (run_id, symbol, statement, fetched_at, source, status) "
        "VALUES (1, 'A', 'income', 'x', 's', 'ok')"
    )
    conn.close()
    conn = db.open_database(path)
    assert db.schema_version(conn) >= 3
    for table in ("runs", "companies", "screener_snapshots", "statement_fetches"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1, table
    assert conn.execute("SELECT last_report_date FROM screener_snapshots").fetchone()[0] is None
    assert conn.execute("SELECT report_date FROM statement_fetches").fetchone()[0] is None


def test_report_date_is_saved_with_snapshot_and_fetch(repo):
    run = repo.start_run("cli")
    repo.save_snapshot(run, "AAA", {"in_screen": 1, "last_report_date": "2026-09-30"})
    assert repo.latest_report_date("AAA") == "2026-09-30"
    assert repo.latest_report_date("ZZZ") is None
    fid = repo.save_statement_fetch(
        "AAA", "income", "x", "ok", [("Revenue", "TTM", 1.0)], report_date="2026-06-30"
    )
    assert repo.latest_statement_fetch("AAA", "income")["report_date"] == "2026-06-30"
    assert fid
