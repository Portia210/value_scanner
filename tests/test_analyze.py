import pytest

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.jobs.analyze import analyse_run
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

YEARS = [2025, 2024, 2023, 2022, 2021]


def good_rows():
    series = {
        R.REVENUE: [1000.0, 950.0, 900.0, 850.0, 800.0],
        R.NET_INCOME: [120.0, 100.0, 90.0, 80.0, 70.0],
        R.EPS_DILUTED: [3.0, 2.8, 2.0, 1.6, 1.4],
        R.GROSS_PROFIT: [400.0, 350.0, 340.0, 330.0, 320.0],
        R.SHARES_DILUTED: [95.0, 100.0, 101.0, 102.0, 103.0],
        R.TOTAL_ASSETS: [1500.0] * 5,
        R.TOTAL_CURRENT_ASSETS: [500.0, 400.0, 400.0, 400.0, 400.0],
        R.TOTAL_CURRENT_LIABILITIES: [200.0] * 5,
        R.TOTAL_DEBT: [100.0] * 5,
        R.LONG_TERM_DEBT: [100.0, 150.0, 150.0, 150.0, 150.0],
        R.TOTAL_LIABILITIES: [300.0] * 5,
        R.EQUITY: [1000.0] * 5,
        R.OPERATING_CASH_FLOW: [150.0] * 5,
        R.FREE_CASH_FLOW: [100.0] * 5,
    }
    out = []
    for item, vals in series.items():
        out += [(item, f"FY {y}", v) for y, v in zip(YEARS, vals, strict=True)]
        out.append((item, "TTM", vals[0]))
    return out


@pytest.fixture
def repo():
    return Repository(db.open_database(":memory:"))


def seed(repo, symbol, sector="Industrials", industry="Machinery", with_statements=True, **snap):
    repo.upsert_company(symbol, name=symbol, sector=sector, industry=industry)
    if with_statements:
        repo.save_statement_fetch(symbol, "income", "t", "ok", good_rows())
    return symbol, snap


def run_with(repo, stocks):
    run = repo.start_run("cli")
    base = {
        "in_screen": 1,
        "market_cap": 3e9,
        "pe_ratio": 10.0,
        "pb_ratio": 1.5,
        "ps_ratio": 1.0,
        "pe_ratio_5y": 20.0,
    }
    for symbol, snap in stocks:
        repo.save_snapshot(run, symbol, {**base, **snap})
    return run


def test_full_analysis_is_stored(repo):
    run = run_with(repo, [seed(repo, "AAA")])
    summary = analyse_run(repo, run)
    assert summary.analysed == 1
    results = repo.results_for(run, "AAA")
    assert len(results) == 8 + 6 + 6 + 8
    assert {r["guru"] for r in results} == {"screen", "graham", "fisher", "piotroski"}
    kinds = {r["kind"]: r for r in repo.conn.execute("SELECT * FROM scores WHERE symbol='AAA'")}
    assert set(kinds) == {"screen", "graham", "fisher", "piotroski", "quality", "opportunity"}
    assert kinds["opportunity"]["score"] is not None
    comps = repo.conn.execute("SELECT COUNT(*) FROM score_components").fetchone()[0]
    assert comps == 4
    labels = [r["label"] for r in repo.conn.execute("SELECT label FROM classifications")]
    assert labels == ["regular"]


def test_only_in_screen_stocks_are_analysed(repo):
    run = run_with(repo, [seed(repo, "AAA"), seed(repo, "BBB", in_screen=0, filters_failed=1)])
    assert analyse_run(repo, run).analysed == 1
    assert repo.results_for(run, "BBB") == []


def test_stock_without_statements_is_na_and_unranked(repo):
    run = run_with(repo, [seed(repo, "AAA", with_statements=False)])
    summary = analyse_run(repo, run)
    assert summary.unranked == ["AAA"] and summary.candidates == []
    statuses = {r["status"] for r in repo.results_for(run, "AAA") if r["guru"] == "graham"}
    assert "PASS" in statuses  # P/E and P/B come from the screener
    q = repo.conn.execute("SELECT score FROM scores WHERE kind='quality'").fetchone()[0]
    assert q is None
    opp = repo.conn.execute("SELECT score FROM scores WHERE kind='opportunity'").fetchone()[0]
    assert opp is not None  # opportunity needs only screener multiples


def test_financial_company_skips_inapplicable_tests(repo):
    run = run_with(repo, [seed(repo, "BANK", sector="Financials", industry="Banks - Regional")])
    analyse_run(repo, run)
    by_id = {(r["guru"], r["criterion_id"]): r for r in repo.results_for(run, "BANK")}
    for key in [("graham", "current_ratio"), ("graham", "working_capital"), ("fisher", "ps")]:
        assert by_id[key]["status"] == Status.NA and "financial" in by_id[key]["note"]
    assert by_id[("graham", "pe")]["status"] != Status.NA


def test_technology_gets_the_looser_pe_limit_and_rd_test(repo):
    stocks = [
        seed(repo, "TECH", sector="Technology", industry="Software - Application", pe_ratio=20.0)
    ]
    run = run_with(repo, stocks)
    analyse_run(repo, run)
    by_id = {(r["guru"], r["criterion_id"]): r for r in repo.results_for(run, "TECH")}
    assert by_id[("graham", "pe")]["status"] == Status.PASS  # 20 < 25
    assert by_id[("graham", "pe")]["threshold"] == 25.0
    assert by_id[("fisher", "rd")]["status"] == Status.NA  # applies, but no R&D rows in fixture


def test_candidate_needs_quality_and_opportunity(repo):
    cheap = seed(repo, "CHEAP", pe_ratio=6.0, pb_ratio=0.8, ps_ratio=0.5)
    dear = seed(repo, "DEAR", pe_ratio=40.0, pb_ratio=8.0, ps_ratio=6.0)
    run = run_with(repo, [cheap, dear])
    summary = analyse_run(repo, run)
    assert "DEAR" not in summary.candidates
    opp = {
        r["symbol"]: r["score"]
        for r in repo.conn.execute("SELECT symbol, score FROM scores WHERE kind='opportunity'")
    }
    assert opp["CHEAP"] > 0.2 > opp["DEAR"]
