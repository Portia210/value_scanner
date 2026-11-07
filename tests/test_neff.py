"""Lesson 8 - Neff: boundaries (at, above, below the threshold; missing; negative)."""

import pytest

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.analysis.gurus.neff import CRITERIA, evaluate_neff
from value_scanner.analysis.statements import Statements


def quarters(values_by_label: dict[str, float | None]) -> list[tuple[str, str, float | None]]:
    return [(R.EPS_DILUTED, label, v) for label, v in values_by_label.items()]


# Four latest fiscal quarters (Q4 2026 .. Q1 2026), each above the same quarter a year earlier.
GOOD_QUARTERS = {
    "Q4 2026": 2.1, "Q3 2026": 2.0, "Q2 2026": 2.0, "Q1 2026": 2.8,
    "Q4 2025": 1.8, "Q3 2025": 1.5, "Q2 2025": 1.6, "Q1 2025": 2.4,
}  # fmt: skip

BASE = dict(
    pe=8.0,
    industry_pe=15.0,  # ratio 0.533
    price=110.0,
    low_52=100.0,
    high_52=200.0,  # position 0.1
    eps_growth_5y=10.0,
    revenue_growth_5y=9.0,  # 0.9 of the EPS growth
    dividend_yield=2.0,  # (10 + 2) / 8 = 1.5
    industry_return_median=0.5,  # limit 1.0
)


def run(rows=None, **over):
    rows = rows if rows is not None else [*quarters(GOOD_QUARTERS), (R.FREE_CASH_FLOW, "TTM", 1.0)]
    rows = [*rows, ("Free Cash Flow Per Share", "TTM", 1.5)] if rows is not None else rows
    s = Statements(rows)
    return {r.criterion_id: r for r in evaluate_neff(s, **{**BASE, **over})}


def test_seven_criteria_in_lesson_order_all_pass_for_a_good_company():
    results = run()
    assert list(results) == list(CRITERIA)
    assert all(r.status == Status.PASS for r in results.values())


# ── 1a: P/E 40%-60% of the industry's: a band, both ends included ───────────────────────────
@pytest.mark.parametrize(
    ("pe", "status"),
    [(6.0, Status.PASS), (9.0, Status.PASS), (5.99, Status.FAIL), (9.01, Status.FAIL)],
)
def test_pe_band_with_industry_pe_15(pe, status):
    assert run(pe=pe)["pe_vs_industry"].status == status


def test_negative_or_zero_pe_fails_and_missing_industry_pe_is_na():
    assert run(pe=-3.0)["pe_vs_industry"].status == Status.FAIL
    assert run(pe=0.0)["pe_vs_industry"].status == Status.FAIL
    assert run(industry_pe=None)["pe_vs_industry"].status == Status.NA
    assert run(industry_pe=0.0)["pe_vs_industry"].status == Status.NA
    assert run(industry_pe=-4.0)["pe_vs_industry"].status == Status.NA
    assert run(pe=None)["pe_vs_industry"].status == Status.NA


# ── 1b: below the middle of the 52-week range ───────────────────────────────────────────────
def test_price_exactly_in_the_middle_fails_and_below_passes():
    assert run(price=150.0)["price_in_range"].status == Status.FAIL
    assert run(price=149.9)["price_in_range"].status == Status.PASS
    assert run(price=150.1)["price_in_range"].status == Status.FAIL
    assert run(price=100.0)["price_in_range"].value == 0.0


def test_range_missing_or_flat_is_na():
    assert run(low_52=None)["price_in_range"].status == Status.NA
    assert run(price=None)["price_in_range"].status == Status.NA
    assert run(low_52=100.0, high_52=100.0)["price_in_range"].status == Status.NA


# ── 2: EPS growth 7%..22%, both ends included ───────────────────────────────────────────────
@pytest.mark.parametrize(
    ("growth", "status"),
    [(7.0, Status.PASS), (22.0, Status.PASS), (6.99, Status.FAIL), (22.01, Status.FAIL),
     (-5.0, Status.FAIL)],
)  # fmt: skip
def test_eps_growth_band(growth, status):
    assert run(eps_growth_5y=growth)["eps_growth"].status == status


def test_eps_growth_falls_back_to_a_cagr_of_five_fiscal_years():
    eps = [1.46, 1.3, 1.2, 1.1, 1.0]  # newest first
    fy = [(R.EPS_DILUTED, f"FY {y}", v) for y, v in zip(range(2025, 2020, -1), eps, strict=True)]
    r = run(rows=fy, eps_growth_5y=None)["eps_growth"]
    assert r.status == Status.PASS and r.note == "computed from 5 fiscal years"
    assert 9 < r.value < 10
    assert run(rows=[], eps_growth_5y=None)["eps_growth"].status == Status.NA


# ── 3: total return at least twice the industry's median ────────────────────────────────────
def test_total_return_at_twice_the_median_passes_and_just_below_fails():
    # value (g + d) / pe with pe 8: growth 10, dividend 2 -> 1.5; limit = 2 x median
    assert run(industry_return_median=0.75)["total_return"].status == Status.PASS  # exactly 2x
    assert run(industry_return_median=0.76)["total_return"].status == Status.FAIL
    assert run(industry_return_median=0.74)["total_return"].status == Status.PASS


def test_total_return_value_and_threshold_are_reported():
    r = run()["total_return"]
    assert (r.value, r.threshold) == (1.5, 1.0)


def test_total_return_is_na_without_data_or_a_meaningful_median():
    for over in (
        {"industry_return_median": None},
        {"industry_return_median": 0.0},
        {"industry_return_median": -0.2},
        {"dividend_yield": None},
        {"pe": -1.0},
        {"pe": 0.0},
    ):
        assert run(**over)["total_return"].status == Status.NA, over


def test_no_dividend_is_zero_not_missing():
    r = run(dividend_yield=0.0)["total_return"]  # (10 + 0) / 8 = 1.25 > 1.0
    assert r.status == Status.PASS and r.value == 1.25


# ── 4: revenue growth at least 70% of EPS growth ────────────────────────────────────────────
def test_organic_growth_boundary_includes_70_percent():
    assert run(eps_growth_5y=10.0, revenue_growth_5y=7.0)["revenue_vs_eps"].status == Status.PASS
    assert run(eps_growth_5y=10.0, revenue_growth_5y=6.99)["revenue_vs_eps"].status == Status.FAIL
    assert run(eps_growth_5y=10.0, revenue_growth_5y=-2.0)["revenue_vs_eps"].status == Status.FAIL


def test_organic_growth_is_na_when_eps_growth_is_not_positive_or_data_missing():
    assert run(eps_growth_5y=0.0)["revenue_vs_eps"].status == Status.NA
    assert run(eps_growth_5y=-4.0)["revenue_vs_eps"].status == Status.NA
    assert run(revenue_growth_5y=None)["revenue_vs_eps"].status == Status.NA


# ── 5: free cash flow per share positive ────────────────────────────────────────────────────
def test_fcf_per_share_boundaries():
    def fcf(v):
        s = Statements([("Free Cash Flow Per Share", "TTM", v)])
        return {r.criterion_id: r for r in evaluate_neff(s, **BASE)}["fcf_per_share"]

    assert fcf(0.01).status == Status.PASS
    assert fcf(0.0).status == Status.FAIL
    assert fcf(-1.0).status == Status.FAIL
    assert fcf(None).status == Status.NA


# ── 6: momentum: each of the last four quarters above the same quarter a year earlier ───────
def momentum(values):
    return run(rows=quarters(values))["momentum"]


def test_all_four_quarters_up_passes():
    r = momentum(GOOD_QUARTERS)
    assert r.status == Status.PASS and r.value == 4.0 and r.strength == 1.0


def test_one_equal_quarter_is_not_growth_and_scores_near_miss():
    r = momentum({**GOOD_QUARTERS, "Q2 2026": 1.6})
    assert r.status == Status.FAIL and r.value == 3.0 and r.strength == 0.25


def test_two_quarters_down_scores_zero():
    r = momentum({**GOOD_QUARTERS, "Q2 2026": 1.0, "Q3 2026": 1.0})
    assert r.status == Status.FAIL and r.value == 2.0 and r.strength == 0.0


def test_a_negative_quarter_that_still_beats_a_worse_one_counts():
    r = momentum({**GOOD_QUARTERS, "Q4 2026": -0.5, "Q4 2025": -1.0})
    assert r.status == Status.PASS


def test_momentum_is_na_without_four_quarters_or_a_year_earlier():
    assert momentum({"Q4 2026": 2.1, "Q3 2026": 2.0, "Q2 2026": 2.0}).status == Status.NA
    gap = {k: v for k, v in GOOD_QUARTERS.items() if k != "Q3 2025"}
    assert momentum(gap).status == Status.NA
    assert momentum({**GOOD_QUARTERS, "Q3 2025": None}).status == Status.NA


def test_the_newest_four_quarters_are_used_even_when_older_ones_exist():
    old = {"Q4 2024": 9.0, "Q3 2024": 9.0, "Q2 2024": 9.0, "Q1 2024": 9.0}  # older, higher
    assert momentum({**GOOD_QUARTERS, **old}).status == Status.PASS


def test_statements_quarter_accessors():
    s = Statements(quarters(GOOD_QUARTERS))
    assert s.latest_quarters(R.EPS_DILUTED, 4) == [(2026, 4), (2026, 3), (2026, 2), (2026, 1)]
    assert s.quarter(R.EPS_DILUTED, 2025, 3) == 1.5
    assert s.quarter(R.EPS_DILUTED, 2019, 3) is None
    assert s.latest_quarters("nope") == []
