"""Lesson 7 - Buffett: boundaries (at, above, below the threshold; missing; negative)."""

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.analysis.gurus.buffett import CRITERIA, evaluate_buffett
from value_scanner.analysis.scoring import guru_score
from value_scanner.analysis.statements import Statements

YEARS = [2025, 2024, 2023, 2022, 2021]


def stmts(**series):
    """Series are newest first; a None entry is a missing value."""
    out = []
    for item, values in series.items():
        out += [(item, f"FY {y}", v) for y, v in zip(YEARS, values, strict=False)]
    return Statements(out)


GOOD = {
    R.EPS_DILUTED: [3.0, 2.8, 2.0, 1.6, 1.4],
    R.NET_INCOME: [120.0, 100.0, 90.0, 80.0, 70.0],  # sum 460
    R.TOTAL_LIABILITIES: [400.0] * 5,
    R.TOTAL_CURRENT_LIABILITIES: [200.0] * 5,  # long-term liabilities 200
    R.TOTAL_ASSETS: [800.0] * 5,  # ROA 15%
    R.EQUITY: [500.0] * 5,  # ROE 24 / 20 / 18 / 16 / 14 -> mean 18.4
    R.RETAINED_EARNINGS: [100.0] * 5,  # (120 - 100) / 100 = 20%
    R.FREE_CASH_FLOW: [50.0] * 5,
}


def run(**over):
    data = {**GOOD, **over}
    return {r.criterion_id: r for r in evaluate_buffett(stmts(**data))}


def test_ten_rows_in_table_order_and_four_are_human_checks():
    results = evaluate_buffett(stmts(**GOOD))
    assert [r.criterion_id for r in results] == list(CRITERIA)
    manual = [r.criterion_id for r in results if r.status == Status.MANUAL]
    assert manual == ["consumer_monopoly", "inflation_pricing", "simple_product", "dcf_price"]
    assert all(r.strength is None for r in results if r.status == Status.MANUAL)


def test_a_good_company_passes_every_computed_test():
    results = run()
    computed = [r for r in results.values() if r.status != Status.MANUAL]
    assert [r.status for r in computed] == [Status.PASS] * 6


def test_human_checks_do_not_count_in_the_score_or_the_coverage():
    results = evaluate_buffett(stmts(**GOOD))
    score = guru_score(results)
    assert (score.total, score.passed, score.coverage) == (6, 6, 1.0)
    assert score.score == 1.0
    # 3 of the 6 computed tests missing: coverage 50% < 60% -> not ranked, even with 4 manual rows
    sparse = evaluate_buffett(stmts(**{R.NET_INCOME: [1.0] * 5}))
    assert guru_score(sparse).score is None


# ── 1: EPS grew every year, no loss year ────────────────────────────────────────────────────
def test_eps_must_rise_in_every_one_of_the_four_steps():
    assert run()["eps_growth"].status == Status.PASS
    assert run()["eps_growth"].value == 4.0


def test_equal_eps_in_one_year_is_not_growth():
    r = run(**{R.EPS_DILUTED: [3.0, 2.8, 2.0, 2.0, 1.4]})["eps_growth"]
    assert r.status == Status.FAIL and r.value == 3.0 and r.strength == 0.25


def test_two_missed_steps_score_zero():
    r = run(**{R.EPS_DILUTED: [3.0, 3.1, 2.0, 2.1, 1.4]})["eps_growth"]
    assert r.status == Status.FAIL and r.value == 2.0 and r.strength == 0.0


def test_a_loss_year_fails_even_when_eps_rises():
    r = run(**{R.NET_INCOME: [120.0, 100.0, 90.0, 80.0, -1.0]})["eps_growth"]
    assert r.status == Status.FAIL and r.note == "a loss year" and r.strength == 0.0


def test_zero_profit_is_not_profitable():
    r = run(**{R.NET_INCOME: [120.0, 100.0, 90.0, 80.0, 0.0]})["eps_growth"]
    assert r.status == Status.FAIL


def test_fewer_than_five_fiscal_years_is_na_never_pass():
    r = run(**{R.EPS_DILUTED: [3.0, 2.8, 2.0, 1.6, None]})["eps_growth"]
    assert r.status == Status.NA


# ── 2: 5-year net income above long-term liabilities ────────────────────────────────────────
def test_net_income_exactly_equal_to_liabilities_fails():
    r = run(**{R.NET_INCOME: [100.0] * 5, R.TOTAL_LIABILITIES: [700.0] * 5})
    # long-term liabilities 700 - 200 = 500 = the 5-year sum
    assert r["earnings_vs_liabilities"].status == Status.FAIL


def test_net_income_just_above_and_below_liabilities():
    above = run(**{R.NET_INCOME: [100.0] * 5, R.TOTAL_LIABILITIES: [699.0] * 5})
    below = run(**{R.NET_INCOME: [100.0] * 5, R.TOTAL_LIABILITIES: [701.0] * 5})
    assert above["earnings_vs_liabilities"].status == Status.PASS
    assert below["earnings_vs_liabilities"].status == Status.FAIL
    assert above["earnings_vs_liabilities"].threshold == 499.0


def test_no_long_term_liabilities_passes_with_positive_income():
    r = run(**{R.TOTAL_LIABILITIES: [200.0] * 5})["earnings_vs_liabilities"]
    assert r.status == Status.PASS and r.threshold == 0.0


def test_missing_liabilities_or_year_is_na_and_nonsense_is_na():
    assert run(**{R.TOTAL_LIABILITIES: [None] * 5})["earnings_vs_liabilities"].status == Status.NA
    assert (
        run(**{R.NET_INCOME: [120.0, 100.0, 90.0, 80.0, None]})["earnings_vs_liabilities"].status
        == Status.NA
    )
    assert run(**{R.TOTAL_LIABILITIES: [100.0] * 5})["earnings_vs_liabilities"].status == Status.NA


# ── 3: ROE 5-year average above 15% ─────────────────────────────────────────────────────────
def test_roe_uses_the_screener_value_first_and_15_is_strict():
    s = stmts(**GOOD)
    at = {r.criterion_id: r for r in evaluate_buffett(s, roe_5y=15.0)}["roe_5y"]
    above = {r.criterion_id: r for r in evaluate_buffett(s, roe_5y=15.01)}["roe_5y"]
    assert at.status == Status.FAIL and above.status == Status.PASS
    assert at.note == "screener value (5-year window)"


def test_roe_falls_back_to_the_statements():
    r = run()["roe_5y"]
    assert r.status == Status.PASS and round(r.value, 1) == 18.4
    assert r.note == "computed from 5 fiscal years"


# ── 4: ROA above 12%, last year ─────────────────────────────────────────────────────────────
def test_roa_boundaries():
    def roa(income):
        return run(**{R.NET_INCOME: [income, 1, 1, 1, 1], R.TOTAL_ASSETS: [1000.0] * 5})["roa"]

    assert roa(120.0).status == Status.FAIL  # exactly 12%
    assert roa(120.1).status == Status.PASS
    assert roa(119.9).status == Status.FAIL
    assert roa(-5.0).status == Status.FAIL and roa(-5.0).value == -0.5


def test_roa_missing_or_no_assets_is_na():
    assert run(**{R.TOTAL_ASSETS: [None] * 5})["roa"].status == Status.NA
    assert run(**{R.TOTAL_ASSETS: [0.0] * 5})["roa"].status == Status.NA


# ── 5: earnings growth against retained earnings, >= 12% (decision B3, open) ─────────────────
def test_retained_earnings_ratio_boundaries_include_12():
    def ratio(now):
        income = [now, 100.0, 90.0, 80.0, 70.0]
        return run(**{R.NET_INCOME: income, R.RETAINED_EARNINGS: [100.0] * 5})

    assert ratio(112.0)["retained_earnings"].status == Status.PASS  # exactly 12%
    assert ratio(111.9)["retained_earnings"].status == Status.FAIL
    assert ratio(112.1)["retained_earnings"].status == Status.PASS


def test_shrinking_profit_is_a_negative_ratio_and_fails():
    r = run(**{R.NET_INCOME: [80.0, 100.0, 90.0, 80.0, 70.0]})["retained_earnings"]
    assert r.status == Status.FAIL and r.value == -20.0


def test_retained_earnings_deficit_or_zero_fails_with_a_note():
    for value in (0.0, -50.0):
        r = run(**{R.RETAINED_EARNINGS: [value] * 5})["retained_earnings"]
        assert r.status == Status.FAIL and "deficit" in r.note


def test_retained_earnings_missing_is_na():
    assert run(**{R.RETAINED_EARNINGS: [None] * 5})["retained_earnings"].status == Status.NA


# ── 6: free cash flow positive, last year (decision B4, open) ───────────────────────────────
def test_free_cash_flow_boundaries():
    def fcf(v):
        return run(**{R.FREE_CASH_FLOW: [v] * 5})["fcf"]

    assert fcf(0.1).status == Status.PASS
    assert fcf(0.0).status == Status.FAIL
    assert fcf(-1.0).status == Status.FAIL
    assert fcf(None).status == Status.NA


def test_a_negative_last_year_fails_even_when_earlier_years_were_positive():
    r = run(**{R.FREE_CASH_FLOW: [-10.0, 50.0, 50.0, 50.0, 50.0]})["fcf"]
    assert r.status == Status.FAIL
