import pytest

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.analysis.gurus.fisher import evaluate_fisher
from value_scanner.analysis.statements import Statements

YEARS = [2025, 2024, 2023, 2022, 2021]


def stmts(**series):
    data = []
    for item, vals in series.items():
        ttm = None
        if isinstance(vals, dict):
            ttm, vals = vals.get("TTM"), vals["FY"]
        if ttm is not None:
            data.append((item, "TTM", ttm))
        data += [(item, f"FY {y}", v) for y, v in zip(YEARS, vals, strict=False)]
    return Statements(data)


GOOD = {
    R.EPS_DILUTED: [3.0, 2.5, 2.0, 1.6, 1.3],  # ~+23% a year
    R.NET_INCOME: [100.0, 90.0, 80.0, 70.0, 60.0],
    R.REVENUE: [1000.0, 950.0, 900.0, 850.0, 800.0],  # margins 10, 9.5, ...
    R.TOTAL_LIABILITIES: {"TTM": 300.0, "FY": [300.0] * 5},
    R.EQUITY: {"TTM": 1000.0, "FY": [1000.0] * 5},
    "Free Cash Flow Per Share": {"TTM": 1.2, "FY": [1.0] * 5},
    R.RESEARCH_AND_DEVELOPMENT: [50.0] * 5,
}


def run(ps=1.0, market_cap=500e6, cyclical=False, rd_applies=True, margin=8.0, **overrides):
    data = {**GOOD, **overrides}
    res = evaluate_fisher(
        stmts(**data),
        ps,
        market_cap,
        cyclical=cyclical,
        rd_applies=rd_applies,
        net_margin_limit=margin,
    )
    return {r.criterion_id: r for r in res}


def test_good_stock_passes_all_six():
    res = run()
    assert len(res) == 6 and {r.status for r in res.values()} == {Status.PASS}
    assert res["rd"].value == pytest.approx(10.0)  # 500M / 50M


@pytest.mark.parametrize(
    ("ps", "cyclical", "status"),
    [
        (1.49, False, Status.PASS),
        (1.5, False, Status.FAIL),
        (0.79, True, Status.PASS),
        (0.8, True, Status.FAIL),
        (1.0, True, Status.FAIL),
        (-2.0, False, Status.FAIL),
        (None, False, Status.NA),
    ],
)
def test_ps_limit_depends_on_cyclicality(ps, cyclical, status):
    r = run(ps=ps, cyclical=cyclical)["ps"]
    assert r.status == status
    if ps is not None and ps < 0:
        assert r.strength == 0.0 and "<= 0" in r.note


def test_eps_growth_is_average_of_yearly_growth_not_endpoints():
    # +100%, then 0%, 0%, 0% -> mean 25%; endpoint CAGR would be only ~19%
    r = run(**{R.EPS_DILUTED: [2.0, 2.0, 2.0, 2.0, 1.0]})["eps_growth"]
    assert r.value == pytest.approx(25.0) and r.status == Status.PASS


def test_eps_growth_boundary_negative_and_loss_base():
    at = run(**{R.EPS_DILUTED: [1.15**4, 1.15**3, 1.15**2, 1.15, 1.0]})["eps_growth"]
    assert at.status == Status.FAIL  # exactly 15 -> not above
    assert run(**{R.EPS_DILUTED: [1.0, 1.0, 1.0, 1.0, -1.0]})["eps_growth"].status == Status.NA
    assert run(**{R.EPS_DILUTED: [1.0, 1.0, None, 1.0, 1.0]})["eps_growth"].status == Status.NA
    shrinking = run(**{R.EPS_DILUTED: [1.0, 2.0, 3.0, 4.0, 5.0]})["eps_growth"]
    assert shrinking.status == Status.FAIL and shrinking.value < 0


def margin(pct, **kw):
    return run(**{R.NET_INCOME: [pct * 10] * 5, R.REVENUE: [1000.0] * 5}, **kw)["net_margin"]


def test_net_margin_limit_is_8_percent_for_ordinary_companies_and_strict():
    assert margin(8.0).status == Status.FAIL  # exactly 8%
    assert margin(8.01).status == Status.PASS
    assert margin(7.99).status == Status.FAIL
    assert margin(8.01).threshold == 8.0


def test_net_margin_limit_is_15_percent_for_technology_and_pharma():
    assert margin(15.0, margin=15.0).status == Status.FAIL  # exactly 15%
    assert margin(15.01, margin=15.0).status == Status.PASS
    assert margin(14.99, margin=15.0).status == Status.FAIL
    assert margin(10.0, margin=15.0).threshold == 15.0  # 10% passes for others, not here
    assert margin(10.0).status == Status.PASS


def test_net_margin_is_always_a_five_year_average():
    mixed = run(**{R.NET_INCOME: [200.0, 0.0, 0.0, 0.0, 0.0], R.REVENUE: [1000.0] * 5})
    assert mixed["net_margin"].value == pytest.approx(4.0)  # (20 + 0 + 0 + 0 + 0) / 5, not 20
    assert mixed["net_margin"].status == Status.FAIL


def test_net_margin_needs_all_five_years_or_it_is_na():
    four = run(**{R.NET_INCOME: [100.0] * 4 + [None], R.REVENUE: [1000.0] * 5})
    assert four["net_margin"].status == Status.NA
    no_revenue = run(**{R.NET_INCOME: [100.0] * 5, R.REVENUE: [1000.0] * 4 + [0.0]})
    assert no_revenue["net_margin"].status == Status.NA  # a year without revenue is not a year
    few = run(**{R.NET_INCOME: [100.0, 100.0, None, None, None], R.REVENUE: [1000.0] * 5})
    assert few["net_margin"].status == Status.NA


def test_net_margin_loss_years_count_and_a_full_loss_scores_zero():
    loss = margin(-10.0)
    assert loss.status == Status.FAIL and loss.strength == 0.0 and loss.value == -10.0


def test_liabilities_to_equity():
    at = run(**{R.TOTAL_LIABILITIES: {"TTM": 400.0, "FY": [400.0] * 5}})["debt_equity"]
    assert at.status == Status.FAIL  # exactly 0.4
    neg = run(**{R.EQUITY: {"TTM": -50.0, "FY": [-50.0] * 5}})["debt_equity"]
    assert neg.status == Status.FAIL and "equity" in neg.note
    assert run(**{R.TOTAL_LIABILITIES: {"FY": [None] * 5}})["debt_equity"].status == Status.NA


def test_fcf_per_share_positive_with_fallback():
    zero = run(**{"Free Cash Flow Per Share": {"TTM": 0.0, "FY": [0.0] * 5}})["fcf"]
    assert zero.status == Status.FAIL  # must be positive
    negative = run(**{"Free Cash Flow Per Share": {"TTM": -0.5, "FY": [0.0] * 5}})["fcf"]
    assert negative.status == Status.FAIL
    fallback = run(
        **{
            "Free Cash Flow Per Share": {"FY": [None] * 5},
            R.FREE_CASH_FLOW: {"TTM": 50.0, "FY": [50.0] * 5},
            R.SHARES_DILUTED: {"TTM": 100.0, "FY": [100.0] * 5},
        }
    )["fcf"]
    assert fallback.status == Status.PASS and fallback.value == pytest.approx(0.5)
    assert run(**{"Free Cash Flow Per Share": {"FY": [None] * 5}})["fcf"].status == Status.NA


@pytest.mark.parametrize(
    ("market_cap", "status"),
    [
        (250e6, Status.PASS),
        (249.9e6, Status.FAIL),
        (750e6, Status.PASS),
        (750.1e6, Status.FAIL),
        (50e6, Status.FAIL),
        (5e9, Status.FAIL),
    ],
)
def test_rd_band_is_inclusive(market_cap, status):
    assert run(market_cap=market_cap)["rd"].status == status  # R&D = 50M -> ratio 5..15


def test_rd_not_applicable_or_missing_is_na():
    assert run(rd_applies=False)["rd"].status == Status.NA
    assert run(**{R.RESEARCH_AND_DEVELOPMENT: [None] * 5})["rd"].status == Status.NA
    assert run(**{R.RESEARCH_AND_DEVELOPMENT: [0.0] * 5})["rd"].status == Status.NA
    assert run(market_cap=None)["rd"].status == Status.NA


def test_everything_missing_is_na():
    res = evaluate_fisher(Statements([]), None, None)
    assert {r.status for r in res} == {Status.NA}
