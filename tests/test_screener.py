import json

import httpx
import pytest

from tests.factories import PASSING, point, screener_json
from value_scanner.jobs.universe import record_universe, refresh_universe
from value_scanner.sources import screener as sc
from value_scanner.sources.screener import (
    FILTERS,
    Blocked,
    ScreenerStock,
    StructureChanged,
    evaluate,
    parse_universe,
)
from value_scanner.storage import db
from value_scanner.storage.repo import Repository


def stock(symbol="AAA", **values):
    return ScreenerStock(symbol, f"{symbol} Corp", 1000, point(**values))


# ── the 8 filters: at, above, below the threshold; missing; negative ─────────────────────────
@pytest.mark.parametrize("name", list(FILTERS))
def test_filter_boundaries(name):
    op, threshold = FILTERS[name]
    good, bad = (threshold + 1, threshold) if op == ">" else (threshold - 0.01, threshold)
    assert evaluate(stock(**{name: good})).passed
    out = evaluate(stock(**{name: bad}))  # exactly at the threshold fails (strict comparison)
    assert not out.passed and out.failed == (name,) and out.missing == ()


@pytest.mark.parametrize("name", list(FILTERS))
def test_missing_value_never_passes(name):
    out = evaluate(stock(**{name: None}))
    assert not out.passed and out.failed == (name,) and out.missing == (name,)


@pytest.mark.parametrize("name", ["revenueGrowth5Y", "epsGrowth5Y", "profitMargin", "roe5y"])
def test_negative_value_fails(name):
    assert evaluate(stock(**{name: -5.0})).failed == (name,)


def test_all_passing_baseline():
    assert evaluate(ScreenerStock("A", "A", 1, point())).passed
    assert set(PASSING) == set(FILTERS)


# ── parsing and structure checks ─────────────────────────────────────────────────────────────
def test_parse_universe_joins_both_responses():
    initial, points = screener_json({"AAA": {}, "BBB": {"marketCap": 1e9}})
    uni = parse_universe(initial, points)
    assert set(uni.stocks) == {"AAA", "BBB"} and uni.stocks["AAA"].volume == 1000


@pytest.mark.parametrize(
    "mutate",
    [
        lambda i, p: i.pop("data"),
        lambda i, p: i["data"].update(rows=[]),
        lambda i, p: i["data"]["columns"].remove("n"),
        lambda i, p: p["data"].update(data={}),
        lambda i, p: p.update(data={}),
    ],
)
def test_parse_universe_shape_errors(mutate):
    initial, points = screener_json({"AAA": {}})
    mutate(initial, points)
    with pytest.raises(StructureChanged):
        parse_universe(initial, points)


def test_parse_universe_field_gone_is_structure_change():
    initial, points = screener_json({f"S{i}": {"peRatio": None} for i in range(20)})
    with pytest.raises(StructureChanged, match="peRatio"):
        parse_universe(initial, points)


# ── share classes (D14) ──────────────────────────────────────────────────────────────────────
def test_dedupe_keeps_most_traded_class():
    a = ScreenerStock("GOOG", "Alphabet Inc.", 100, {})
    b = ScreenerStock("GOOGL", "Alphabet Inc.", 300, {})
    c = ScreenerStock("MSFT", "Microsoft", 5, {})
    kept, dropped = sc.dedupe_share_classes([a, b, c])
    assert [s.symbol for s in kept] == ["GOOGL", "MSFT"] and dropped == ["GOOG"]


def test_dedupe_tie_is_deterministic():
    a = ScreenerStock("X.B", "Same", None, {})
    b = ScreenerStock("X.A", "Same", None, {})
    assert sc.dedupe_share_classes([a, b])[0][0].symbol == "X.A"


# ── fetching (httpx mock) ────────────────────────────────────────────────────────────────────
def mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), headers=sc.HEADERS)


def test_fetch_universe_two_requests_with_literal_plus(monkeypatch):
    initial, points = screener_json({"AAA": {}})
    seen = []

    def handler(request):
        seen.append(str(request.url))
        body = points if "data-points" in request.url.path else initial
        return httpx.Response(200, json=body)

    pauses = []
    uni = sc.fetch_universe(mock_client(handler), pause=4.0, sleep=pauses.append)
    assert "AAA" in uni.stocks and len(seen) == 2 and pauses == [4.0]
    assert "ids=marketCap+peRatio+" in seen[1] and "%2B" not in seen[1]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, text="forbidden"),
        httpx.Response(429, text="slow down"),
        httpx.Response(200, text="<html><title>Just a moment...</title>"),
        httpx.Response(200, headers={"cf-mitigated": "challenge"}, text="{}"),
    ],
)
def test_fetch_universe_blocked(response):
    with pytest.raises(Blocked):
        sc.fetch_universe(mock_client(lambda r: response), sleep=lambda s: None)


def test_fetch_universe_server_error_is_not_blocked():
    with pytest.raises(httpx.HTTPStatusError):
        sc.fetch_universe(
            mock_client(lambda r: httpx.Response(500, text="oops")), sleep=lambda s: None
        )


# ── persisting runs and membership events ────────────────────────────────────────────────────
@pytest.fixture
def repo():
    r = Repository(db.open_database(":memory:"))
    return r


def run_with(repo, stocks):
    initial, points = screener_json(stocks)
    run = repo.start_run("cli")
    result = record_universe(repo, run, parse_universe(initial, points))
    repo.finish_run(run, "ok")
    return run, result


def events(repo):
    return {(e["symbol"], e["direction"]): e for e in repo.membership_events()}


def test_first_run_stores_in_screen_and_almost_only(repo):
    run, res = run_with(
        repo,
        {
            "PASS": {},
            "ALMOST": {"debtEquity": 0.9, "currentRatio": 1.0},  # fails 2 filters
            "FAR": {"debtEquity": 0.9, "currentRatio": 1.0, "roe5y": 1.0},  # fails 3
            "NODATA": {"epsGrowth5Y": None},  # fails 1 (missing) -> almost
        },
    )
    assert res.in_screen == ["PASS"] and sorted(res.almost) == ["ALMOST", "NODATA"]
    snaps = repo.snapshots_for_run(run)
    assert set(snaps) == {"PASS", "ALMOST", "NODATA"}
    assert snaps["PASS"]["in_screen"] == 1 and snaps["ALMOST"]["filters_failed"] == 2
    assert snaps["PASS"]["price"] == 50.0 and snaps["PASS"]["pocf_ratio"] == 10.0
    assert repo.get_company("PASS")["sector"] == "Industrials"
    assert repo.get_company("FAR") is None
    assert repo.membership_events() == []  # nothing to compare with yet
    assert repo.get_setting("universe_count") == "4"


def test_entering_because_of_price(repo):
    run_with(repo, {"AAA": {"peRatio": 4.0}, "BBB": {}})
    _, res = run_with(repo, {"AAA": {"peRatio": 6.0}, "BBB": {}})
    ev = events(repo)[("AAA", "enter")]
    assert res.entered == ["AAA"] and ev["reason_type"] == "price"
    assert json.loads(ev["detail"]) == {"peRatio": {"before": 4.0, "after": 6.0}}


def test_leaving_because_of_new_report(repo):
    run_with(repo, {"AAA": {}})
    run_with(repo, {"AAA": {"profitMargin": 5.0, "lastEarningsDate": "2026-11-04"}})
    ev = events(repo)[("AAA", "exit")]
    assert ev["reason_type"] == "report"
    assert json.loads(ev["detail"])["profitMargin"] == {"before": 12.0, "after": 5.0}


def test_report_reason_when_non_price_filter_flips_without_new_date(repo):
    run_with(repo, {"AAA": {"debtEquity": 0.7}})
    run_with(repo, {"AAA": {"debtEquity": 0.4}})
    assert events(repo)[("AAA", "enter")]["reason_type"] == "report"


def test_missing_value_flip_is_data(repo):
    # PAD keeps the field's coverage above the structure-change threshold
    run_with(repo, {"AAA": {}, "PAD": {}})
    run_with(repo, {"AAA": {"epsGrowth5Y": None}, "PAD": {}})
    assert events(repo)[("AAA", "exit")]["reason_type"] == "data"


def test_new_symbol_and_delisted(repo):
    run_with(repo, {"OLD": {}})
    run_with(repo, {"NEW": {}})
    ev = events(repo)
    assert ev[("NEW", "enter")]["reason_type"] == "new_symbol"
    assert ev[("OLD", "exit")]["reason_type"] == "delisted"


def test_unchanged_run_has_no_events(repo):
    run_with(repo, {"AAA": {}, "BBB": {"peRatio": 4.0}})
    run_with(repo, {"AAA": {}, "BBB": {"peRatio": 4.0}})
    assert repo.membership_events() == []


def test_share_class_swap_is_not_a_membership_change(repo):
    run_with(
        repo,
        {"GOOG": {"name": "Alphabet", "volume": 300}, "GOOGL": {"name": "Alphabet", "volume": 100}},
    )
    _, res = run_with(
        repo,
        {"GOOG": {"name": "Alphabet", "volume": 100}, "GOOGL": {"name": "Alphabet", "volume": 300}},
    )
    assert res.in_screen == ["GOOGL"] and res.dropped_share_classes == ["GOOG"]
    assert repo.membership_events() == []


def test_shrinking_universe_raises_and_stores_nothing(repo):
    run_with(repo, {f"S{i}": {} for i in range(10)})
    run = repo.start_run("cli")
    initial, points = screener_json({f"S{i}": {} for i in range(5)})
    with pytest.raises(StructureChanged, match="shrank"):
        record_universe(repo, run, parse_universe(initial, points))
    assert repo.snapshots_for_run(run) == {}
    assert repo.get_setting("universe_count") == "10"


def test_refresh_universe_alerts_on_block_and_structure_change(repo):
    run = repo.start_run("cli")

    def blocked():
        raise Blocked("HTTP 403")

    with pytest.raises(Blocked):
        refresh_universe(repo, run, fetch=blocked)

    def changed():
        raise StructureChanged("fields gone")

    with pytest.raises(StructureChanged):
        refresh_universe(repo, run, fetch=changed)
    kinds = [a["kind"] for a in repo.conn.execute("SELECT kind FROM alerts ORDER BY id")]
    assert kinds == ["blocked", "structure_changed"]
    assert [m["level"] for m in repo.run_log(run)] == ["error", "error"]
