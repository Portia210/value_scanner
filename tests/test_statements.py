import random
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from tests.factories import statement_html
from value_scanner.jobs.refresh import (
    FULL_REFRESH_DAYS,
    Pacing,
    download_statements,
    refresh_reason,
)
from value_scanner.sources.screener import Blocked
from value_scanner.sources.stockanalysis import (
    HEADERS,
    ParseError,
    StatementFetcher,
    parse_number,
    parse_statement_table,
    statement_url,
)
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

# ── parsing ──────────────────────────────────────────────────────────────────────────────────


def test_parse_statement_table_long_format():
    rows, latest = parse_statement_table(statement_html())
    got = {(i, p): v for i, p, v in rows}
    assert got[("Revenue", "TTM")] == 1316.0 and got[("Revenue", "FY 2023")] == 1169.0
    assert got[("Revenue Growth (YoY) (%)", "FY 2024")] == 2.75  # '%' row gets the v1 suffix
    assert got[("Revenue Growth (YoY) (%)", "FY 2023")] is None  # '-' is missing, not zero
    assert latest == "FY 2024"  # newest fiscal year, TTM skipped
    assert len(rows) == 9


def test_percent_suffix_not_duplicated():
    rows, _ = parse_statement_table(statement_html([["Margin (%)", "5%", "6%", "7%"]]))
    assert {i for i, _, _ in rows} == {"Margin (%)"}


def test_upgrade_columns_are_skipped():
    html = statement_html(
        [["Revenue", "1", "2", "3", "Upgrade"]],
        periods=("Fiscal Year", "TTM", "FY 2024", "FY 2023", "Upgrade"),
    )
    rows, _ = parse_statement_table(html)
    assert {p for _, p, _ in rows} == {"TTM", "FY 2024", "FY 2023"}


def test_no_table_returns_empty():
    assert parse_statement_table("<html><body>Overview</body></html>") == ([], None)


@pytest.mark.parametrize(
    "html",
    [
        statement_html([["Revenue", "1", "2"]]),  # too few cells
        statement_html([["Revenue", "abc", "2", "3"]]),  # not a number
        statement_html([]),  # no rows
        statement_html(periods=("Fiscal Year",)),  # no period columns
    ],
)
def test_malformed_tables_raise(html):
    with pytest.raises(ParseError):
        parse_statement_table(html)


@pytest.mark.parametrize(
    ("text", "value"),
    [("1,316.0", 1316.0), ("-5.5", -5.5), ("8.77%", 8.77), ("$3", 3.0), ("-", None), ("", None)],
)
def test_parse_number(text, value):
    assert parse_number(text) == value


def test_statement_url_uses_lowercase_dotted_symbol():
    assert statement_url("BRK.B", "income") == (
        "https://stockanalysis.com/stocks/brk.b/financials/income-statement/"
    )
    assert statement_url("AAON", "metrics").endswith("/aaon/financials/metrics/")


# ── fetching outcomes ────────────────────────────────────────────────────────────────────────
def fetcher_for(handler, sleeps=None):
    client = httpx.Client(transport=httpx.MockTransport(handler), headers=HEADERS)
    return StatementFetcher(
        client, retries=2, retry_wait=5.0, sleep=(sleeps if sleeps is not None else []).append
    )


def test_fetch_ok():
    out = fetcher_for(lambda r: httpx.Response(200, text=statement_html())).fetch("AAA", "income")
    assert out.status == "ok" and out.latest_period == "FY 2024" and len(out.rows) == 9


@pytest.mark.parametrize(
    ("response", "status"),
    [
        (httpx.Response(404, text="nope"), "failed"),
        (httpx.Response(403, text="x"), "failed"),
        (httpx.Response(429, text="slow"), "blocked"),
        (httpx.Response(200, text="<title>Just a moment...</title>"), "blocked"),
        (httpx.Response(403, headers={"cf-mitigated": "challenge"}, text="x"), "blocked"),
        (httpx.Response(200, text="<html>Overview page</html>"), "no_table"),
        (httpx.Response(200, text=statement_html([["Revenue", "oops", "1", "2"]])), "failed"),
    ],
)
def test_fetch_classifies_outcomes(response, status):
    assert fetcher_for(lambda r: response).fetch("AAA", "income").status == status


def test_server_error_retries_are_bounded():
    calls, sleeps = [], []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, text="down")

    out = fetcher_for(handler, sleeps).fetch("AAA", "income")
    assert out.status == "failed" and len(calls) == 3 and sleeps == [5.0, 10.0]


def test_transport_error_then_success():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, text=statement_html())

    assert fetcher_for(handler).fetch("AAA", "income").status == "ok"


def test_transport_error_forever_gives_up():
    def handler(request):
        raise httpx.ConnectError("boom")

    out = fetcher_for(handler).fetch("AAA", "income")
    assert out.status == "failed" and "ConnectError" in out.detail


def test_challenge_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(403, headers={"cf-mitigated": "challenge"}, text="x")

    assert fetcher_for(handler).fetch("AAA", "income").status == "blocked" and len(calls) == 1


# ── when to refresh (D18) ────────────────────────────────────────────────────────────────────
NOW = datetime(2026, 6, 30, 12, tzinfo=UTC)


def at(days_ago):
    return NOW - timedelta(days=days_ago)


def test_new_stock_is_fetched_immediately():
    assert refresh_reason(NOW, [], None, False) == "new"


def test_fresh_stock_without_earnings_is_skipped():
    assert refresh_reason(NOW, [at(5)], None, False) is None
    assert refresh_reason(NOW, [at(5)], date(2026, 8, 1), False) is None  # earnings in the future


def test_full_refresh_every_45_days():
    assert refresh_reason(NOW, [at(FULL_REFRESH_DAYS - 1)], None, False) is None
    assert refresh_reason(NOW, [at(FULL_REFRESH_DAYS)], None, False) == "full_refresh"


def test_earnings_retries_at_1_3_7_days():
    e = date(2026, 6, 20)
    old = datetime(2026, 6, 1, 12, tzinfo=UTC)  # baseline fetch before earnings
    # day 0 (earnings day) and the day before the first retry: not yet
    assert refresh_reason(datetime(2026, 6, 20, 18, tzinfo=UTC), [old], e, False) is None
    assert refresh_reason(datetime(2026, 6, 21, 8, tzinfo=UTC), [old], e, False) == "earnings_try_1"
    # first retry done on the 21st (no change) -> wait for day 3
    t1 = datetime(2026, 6, 21, 9, tzinfo=UTC)
    assert refresh_reason(datetime(2026, 6, 22, 9, tzinfo=UTC), [t1, old], e, False) is None
    assert refresh_reason(datetime(2026, 6, 23, 9, tzinfo=UTC), [t1, old], e, False) == (
        "earnings_try_2"
    )
    t2 = datetime(2026, 6, 23, 9, tzinfo=UTC)
    assert refresh_reason(datetime(2026, 6, 26, 9, tzinfo=UTC), [t2, t1, old], e, False) is None
    assert refresh_reason(datetime(2026, 6, 27, 9, tzinfo=UTC), [t2, t1, old], e, False) == (
        "earnings_try_3"
    )
    t3 = datetime(2026, 6, 27, 9, tzinfo=UTC)
    # three tries without a change: stop until the 45-day refresh
    assert refresh_reason(datetime(2026, 7, 10, 9, tzinfo=UTC), [t3, t2, t1, old], e, False) is None


def test_new_period_stops_the_retries():
    e = date(2026, 6, 20)
    old = datetime(2026, 6, 1, 12, tzinfo=UTC)
    t1 = datetime(2026, 6, 21, 9, tzinfo=UTC)
    assert refresh_reason(datetime(2026, 6, 25, tzinfo=UTC), [t1, old], e, True) is None


def test_first_ever_fetch_after_earnings_needs_no_retries():
    e = date(2026, 6, 20)
    first = datetime(2026, 6, 25, 9, tzinfo=UTC)  # no baseline from before the report
    assert refresh_reason(datetime(2026, 6, 28, tzinfo=UTC), [first], e, False) is None


# ── download loop ────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def repo():
    state = {"t": NOW}
    r = Repository(db.open_database(":memory:"), lambda: state["t"])
    r.state = state
    for s in ("AAA", "BBB", "CCC"):
        r.upsert_company(s)
    return r


def run_download(repo, handler, symbols=("AAA", "BBB", "CCC"), statements=("income",), **kw):
    sleeps = []
    pacing = kw.pop("pacing", Pacing())
    summary = download_statements(
        repo,
        None,
        fetcher_for(handler),
        symbols,
        statements=statements,
        pacing=pacing,
        sleep=sleeps.append,
        rng=random.Random(1),
        **kw,
    )
    return summary, sleeps


OK = lambda r: httpx.Response(200, text=statement_html())  # noqa: E731


def test_download_saves_to_db_and_paces(repo):
    summary, sleeps = run_download(repo, OK, statements=("income", "balance_sheet"))
    assert (summary.ok, summary.failed) == (6, 0)
    assert len(sleeps) == 5  # between requests, none after the last
    assert all(3.0 <= s <= 6.0 for s in sleeps)
    fetch = repo.latest_statement_fetch("AAA", "balance_sheet")
    assert fetch["latest_period"] == "FY 2024" and fetch["source"] == "stockanalysis"
    assert len(repo.statement_values(fetch["id"])) == 9


def test_fresh_statements_are_skipped(repo):
    run_download(repo, OK)
    repo.state["t"] = NOW + timedelta(days=3)
    calls = []
    summary, sleeps = run_download(repo, lambda r: calls.append(1) or OK(r))
    assert calls == [] and summary.skipped_fresh == 3 and sleeps == []


def test_one_failing_stock_does_not_stop_the_run(repo):
    def handler(request):
        if "/bbb/" in request.url.path:
            return httpx.Response(404, text="gone")
        if "/ccc/" in request.url.path:
            return httpx.Response(200, text="<html>no table</html>")
        return httpx.Response(200, text=statement_html())

    progress = []
    summary, _ = run_download(repo, handler, on_progress=lambda d, t: progress.append((d, t)))
    assert (summary.ok, summary.failed, summary.no_table) == (1, 1, 1)
    assert [f.split(":")[0] for f in summary.failures] == ["BBB/income", "CCC/income"]
    assert progress == [(1, 3), (2, 3), (3, 3)]
    statuses = {
        r["symbol"]: r["status"] for r in repo.conn.execute("SELECT * FROM statement_fetches")
    }
    assert statuses == {"AAA": "ok", "BBB": "failed", "CCC": "no_table"}
    kinds = [r["kind"] for r in repo.conn.execute("SELECT kind FROM parse_failures ORDER BY id")]
    assert kinds == ["failed", "no_table"]


def test_block_waits_then_retries_same_item(repo):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(403, headers={"cf-mitigated": "challenge"}, text="x")
        return httpx.Response(200, text=statement_html())

    summary, sleeps = run_download(repo, handler, symbols=("AAA",), pacing=Pacing(block_wait=600.0))
    assert summary.ok == 1 and sleeps == [600.0]
    blocked = repo.conn.execute("SELECT COUNT(*) FROM statement_fetches WHERE status='blocked'")
    assert blocked.fetchone()[0] == 1


def test_repeated_blocks_abort_the_batch(repo):
    def handler(request):
        return httpx.Response(429, text="slow down")

    with pytest.raises(Blocked):
        run_download(repo, handler, pacing=Pacing(max_blocks_in_a_row=3, block_wait=1.0))
    assert repo.conn.execute("SELECT COUNT(*) FROM statement_fetches").fetchone()[0] == 3


def test_long_rest_after_many_requests(repo):
    for i in range(10):
        repo.upsert_company(f"S{i}")
    pacing = Pacing(pause=(3, 3), rest_every=(4, 4), rest=(100, 100))
    _, sleeps = run_download(repo, OK, symbols=[f"S{i}" for i in range(10)], pacing=pacing)
    assert sleeps == [3, 3, 3, 100, 3, 3, 3, 100, 3]  # rest after every 4th request


def test_earnings_triggers_refresh_via_snapshot(repo):
    run = repo.start_run("cli")
    repo.save_snapshot(run, "AAA", {"in_screen": 1, "last_earnings_date": "2026-06-25"})
    repo.finish_run(run, "ok")
    repo.state["t"] = datetime(2026, 6, 1, tzinfo=UTC)
    run_download(repo, OK, symbols=("AAA",))
    repo.state["t"] = datetime(2026, 6, 26, 9, tzinfo=UTC)  # day after earnings
    summary, _ = run_download(repo, OK, symbols=("AAA",))
    assert summary.ok == 1
    # table unchanged -> try again on day 3, not before
    repo.state["t"] = datetime(2026, 6, 27, 9, tzinfo=UTC)
    assert run_download(repo, OK, symbols=("AAA",))[0].skipped_fresh == 1
    repo.state["t"] = datetime(2026, 6, 28, 9, tzinfo=UTC)
    assert run_download(repo, OK, symbols=("AAA",))[0].ok == 1


def test_changed_table_after_earnings_stops_retries(repo):
    run = repo.start_run("cli")
    repo.save_snapshot(run, "AAA", {"in_screen": 1, "last_earnings_date": "2026-06-25"})
    repo.state["t"] = datetime(2026, 6, 1, tzinfo=UTC)
    run_download(repo, OK, symbols=("AAA",))
    new_html = statement_html([["Revenue", "1,400.0", "1,201.0", "1,169.0"]])
    repo.state["t"] = datetime(2026, 6, 26, 9, tzinfo=UTC)
    run_download(repo, lambda r: httpx.Response(200, text=new_html), symbols=("AAA",))
    repo.state["t"] = datetime(2026, 6, 28, 9, tzinfo=UTC)
    assert run_download(repo, OK, symbols=("AAA",))[0].skipped_fresh == 1
