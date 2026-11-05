import math

import pytest

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.analysis.gurus.screen import CRITERIA, cagr_pct, evaluate_screen
from value_scanner.analysis.statements import Statements

YEARS = [2025, 2024, 2023, 2022, 2021]


def stmts(**series):
    """series: item -> list of 5 FY values (newest first) or a dict {"TTM": x, "FY": [...]}."""
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
    R.REVENUE: {"TTM": 1000.0, "FY": [1000.0, 900.0, 800.0, 700.0, 600.0]},
    R.NET_INCOME: {"TTM": 120.0, "FY": [120.0, 100.0, 90.0, 80.0, 70.0]},
    R.EPS_DILUTED: [3.0, 2.5, 2.2, 2.0, 1.8],
    R.TOTAL_DEBT: {"TTM": 200.0, "FY": [200.0, 180.0, 170.0, 160.0, 150.0]},
    R.EQUITY: {"TTM": 800.0, "FY": [800.0, 700.0, 650.0, 600.0, 550.0]},
    R.TOTAL_CURRENT_ASSETS: {"TTM": 500.0, "FY": [500.0, 450.0, 400.0, 380.0, 350.0]},
    R.TOTAL_CURRENT_LIABILITIES: {"TTM": 200.0, "FY": [200.0, 190.0, 180.0, 170.0, 160.0]},
}


def run(market_cap=3e9, pe=15.0, **overrides):
    data = {**GOOD, **overrides}
    return {r.criterion_id: r for r in evaluate_screen(stmts(**data), market_cap, pe)}


def test_good_stock_passes_all_eight():
    res = run()
    assert set(res) == set(CRITERIA) and len(res) == 8
    assert {r.status for r in res.values()} == {Status.PASS}


def test_values_are_the_stated_formulas():
    res = run()
    assert res["profit_margin"].value == pytest.approx(12.0)
    assert res["debt_equity"].value == pytest.approx(0.25)
    assert res["current_ratio"].value == pytest.approx(2.5)
    assert res["revenue_growth_5y"].value == pytest.approx(((1000 / 600) ** 0.25 - 1) * 100)


@pytest.mark.parametrize(
    ("kwargs", "criterion", "status"),
    [
        ({"market_cap": 2e9}, "market_cap", Status.FAIL),  # at the threshold
        ({"market_cap": 2.0001e9}, "market_cap", Status.PASS),
        ({"pe": 5.0}, "pe", Status.FAIL),
        ({"pe": 5.01}, "pe", Status.PASS),
        ({"pe": None}, "pe", Status.NA),
        ({"pe": -3.0}, "pe", Status.FAIL),
        ({"market_cap": math.nan}, "market_cap", Status.NA),
    ],
)
def test_screener_inputs(kwargs, criterion, status):
    assert run(**kwargs)[criterion].status == status


def test_profit_margin_boundary():
    at = run(**{R.NET_INCOME: {"TTM": 80.0, "FY": [80.0] * 5}})["profit_margin"]  # exactly 8%
    above = run(**{R.NET_INCOME: {"TTM": 80.1, "FY": [80.0] * 5}})["profit_margin"]
    assert at.status == Status.FAIL and above.status == Status.PASS


def test_profit_margin_negative_and_missing():
    neg = run(**{R.NET_INCOME: {"TTM": -50.0, "FY": [-50.0] * 5}})["profit_margin"]
    assert neg.status == Status.FAIL and neg.strength == 0.0
    assert run(**{R.REVENUE: {"FY": [None] * 5}})["profit_margin"].status == Status.NA


def test_growth_needs_five_years_and_positive_base():
    short = Statements([(R.REVENUE, f"FY {y}", 100.0 + i) for i, y in enumerate(YEARS[:3])])
    assert cagr_pct(short.series(R.REVENUE, 5)) is None  # oldest slot missing
    negative_base = run(**{R.EPS_DILUTED: [3.0, 2.0, 1.0, 0.5, -1.0]})["eps_growth_5y"]
    assert negative_base.status == Status.NA  # growth from a loss is not a growth rate
    declining = run(**{R.REVENUE: [500.0, 600.0, 700.0, 800.0, 900.0]})["revenue_growth_5y"]
    assert declining.status == Status.FAIL and declining.value < 0


def test_flat_growth_fails_strict_threshold():
    flat = run(**{R.REVENUE: [100.0] * 5})["revenue_growth_5y"]
    assert flat.value == pytest.approx(0.0) and flat.status == Status.FAIL


def test_debt_equity_boundaries_and_negative_equity():
    at = run(**{R.TOTAL_DEBT: {"TTM": 400.0, "FY": [400.0] * 5}})["debt_equity"]  # 0.5
    assert at.status == Status.FAIL
    neg = run(**{R.EQUITY: {"TTM": -100.0, "FY": [-100.0] * 5}})["debt_equity"]
    assert neg.status == Status.FAIL and "equity" in neg.note
    assert run(**{R.TOTAL_DEBT: {"FY": [None] * 5}})["debt_equity"].status == Status.NA


def test_zero_debt_passes():
    r = run(**{R.TOTAL_DEBT: {"TTM": 0.0, "FY": [0.0] * 5}})["debt_equity"]
    assert r.status == Status.PASS and r.value == 0.0


def test_current_ratio_boundary_and_zero_liabilities():
    at = run(**{R.TOTAL_CURRENT_ASSETS: {"TTM": 400.0, "FY": [400.0] * 5}})["current_ratio"]
    assert at.status == Status.FAIL  # exactly 2.0
    zero = run(**{R.TOTAL_CURRENT_LIABILITIES: {"TTM": 0.0, "FY": [0.0] * 5}})["current_ratio"]
    assert zero.status == Status.NA


def test_roe_average_skips_bad_years_and_needs_three():
    # years 2 and 3 have no usable equity; three valid years remain
    eq = [800.0, 700.0, None, -5.0, 550.0]
    r = run(**{R.EQUITY: {"TTM": 800.0, "FY": eq}})["roe_5y"]
    expected = (120 / 800 + 100 / 700 + 70 / 550) / 3 * 100
    assert r.value == pytest.approx(expected) and r.status == Status.PASS
    too_few = run(**{R.EQUITY: {"TTM": 800.0, "FY": [800.0, 700.0, None, None, None]}})["roe_5y"]
    assert too_few.status == Status.NA


def test_everything_missing_is_na_not_pass():
    res = {r.criterion_id: r for r in evaluate_screen(Statements([]), None, None)}
    assert {r.status for r in res.values()} == {Status.NA}
