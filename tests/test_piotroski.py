import pytest

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.analysis.gurus.piotroski import evaluate_piotroski
from value_scanner.analysis.statements import Statements


def stmts(**pairs):
    """item -> (FY0, FY1)."""
    data = []
    for item, (now, before) in pairs.items():
        data += [(item, "FY 2025", now), (item, "FY 2024", before)]
    return Statements(data)


GOOD = {
    R.TOTAL_CURRENT_ASSETS: (500.0, 400.0),
    R.TOTAL_CURRENT_LIABILITIES: (200.0, 200.0),  # 2.5 vs 2.0
    R.LONG_TERM_DEBT: (100.0, 150.0),
    R.TOTAL_ASSETS: (1000.0, 1000.0),  # LT debt/assets 0.10 vs 0.15
    R.OPERATING_CASH_FLOW: (150.0, 120.0),
    R.NET_INCOME: (100.0, 80.0),  # ROA 0.10 vs 0.08; OCF > NI
    R.SHARES_DILUTED: (95.0, 100.0),
    R.GROSS_PROFIT: (400.0, 350.0),
    R.REVENUE: (1000.0, 950.0),  # GM 0.40 vs 0.368; turnover 1.0 vs 0.95
}


def run(**overrides):
    data = {**GOOD, **overrides}
    return {r.criterion_id: r for r in evaluate_piotroski(stmts(**data))}


def test_improving_company_passes_the_seven_statement_tests():
    res = run()
    assert len(res) == 7 and "pb_discount" not in res  # the equity-multiple test is gone
    assert {r.status for r in res.values()} == {Status.PASS}
    assert res["current_ratio"].value == pytest.approx(2.5)
    assert res["current_ratio"].threshold == pytest.approx(2.0)  # last year's figure


@pytest.mark.parametrize(
    ("override", "criterion"),
    [
        ({R.TOTAL_CURRENT_ASSETS: (400.0, 400.0)}, "current_ratio"),  # equal is not better
        ({R.TOTAL_CURRENT_ASSETS: (300.0, 400.0)}, "current_ratio"),
        ({R.LONG_TERM_DEBT: (150.0, 150.0)}, "lt_debt_assets"),
        ({R.LONG_TERM_DEBT: (200.0, 150.0)}, "lt_debt_assets"),
        ({R.SHARES_DILUTED: (100.0, 100.0)}, "shares"),
        ({R.SHARES_DILUTED: (110.0, 100.0)}, "shares"),
        ({R.GROSS_PROFIT: (350.0, 350.0)}, "gross_margin"),
        ({R.REVENUE: (900.0, 950.0)}, "asset_turnover"),
    ],
)
def test_each_comparison_fails_when_not_improved(override, criterion):
    r = run(**override)[criterion]
    assert r.status == Status.FAIL and r.strength == 0.0


def test_cash_flow_must_be_positive_and_above_income():
    assert run(**{R.OPERATING_CASH_FLOW: (100.0, 0.0)})["cash_flow"].status == Status.FAIL  # = NI
    assert (
        run(**{R.OPERATING_CASH_FLOW: (-5.0, 0.0), R.NET_INCOME: (-50.0, 0.0)})["cash_flow"].status
        == Status.FAIL
    )  # above a loss, but negative
    assert run(**{R.OPERATING_CASH_FLOW: (None, 1.0)})["cash_flow"].status == Status.NA


def test_roa_must_be_positive_and_improving():
    # a smaller loss is an improvement but ROA is still negative
    loss = run(**{R.NET_INCOME: (-10.0, -80.0)})["roa"]
    assert loss.status == Status.FAIL and "<= 0" in loss.note
    assert run(**{R.NET_INCOME: (80.0, 80.0)})["roa"].status == Status.FAIL


def test_missing_long_term_debt_row_means_zero_debt():
    no_row = {R.LONG_TERM_DEBT: (None, None)}
    assert run(**no_row)["lt_debt_assets"].status == Status.FAIL  # 0 vs 0: not lower
    r = run(**{R.LONG_TERM_DEBT: (None, 150.0)})["lt_debt_assets"]
    assert r.status == Status.PASS and r.value == 0.0  # 0 < 0.15
    # Total Debt is never used as a substitute
    with_total = {R.LONG_TERM_DEBT: (None, None), R.TOTAL_DEBT: (500.0, 100.0)}
    assert run(**with_total)["lt_debt_assets"].value == 0.0


def test_no_balance_sheet_makes_the_debt_test_na():
    s = Statements([(R.REVENUE, "FY 2025", 1.0), (R.REVENUE, "FY 2024", 1.0)])
    res = {r.criterion_id: r for r in evaluate_piotroski(s)}
    assert res["lt_debt_assets"].status == Status.NA


def test_missing_previous_year_is_na_not_pass():
    s = Statements([(R.TOTAL_CURRENT_ASSETS, "FY 2025", 5.0)])
    res = {r.criterion_id: r for r in evaluate_piotroski(s)}
    assert {r.status for r in res.values()} == {Status.NA}


def test_zero_or_negative_denominators_are_na():
    r = run(**{R.TOTAL_CURRENT_LIABILITIES: (0.0, 200.0)})["current_ratio"]
    assert r.status == Status.NA
