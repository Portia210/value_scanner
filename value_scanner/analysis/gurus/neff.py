"""Lesson 8 - John Neff (C12): cheap against the industry for the right reason, moderate growth,
a total return twice the benchmark, organic growth, positive free cash flow, and momentum.

Benchmarks follow the developer's decisions of 2026-11-07: the P/E is compared with the industry's
P/E (the site's own figure) and the total return with the median of the industry. Every reading
the lesson leaves open is listed in docs/formula-decisions.md (items N1-N9).
"""

from __future__ import annotations

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import (
    Criterion,
    Result,
    Status,
    evaluate,
    is_missing,
    strength,
)
from value_scanner.analysis.gurus.fisher import fcf_per_share
from value_scanner.analysis.gurus.screen import cagr_pct
from value_scanner.analysis.statements import Statements

GURU = "neff"
PE_LOW, PE_HIGH = 0.4, 0.6  # P/E as a share of the industry's: "lower by 40%-60%"
EPS_GROWTH_LOW, EPS_GROWTH_HIGH = 7.0, 22.0
TOTAL_RETURN_FACTOR = 2.0
ORGANIC_MIN = 0.7
RANGE_MIDDLE = 0.5
QUARTERS = 4


def _c(cid: str, title: str, formula: str, direction: str, threshold: float, note: str = ""):
    return Criterion(cid, GURU, 8, title, formula, direction, threshold, note)


CRITERIA = {
    c.id: c
    for c in (
        _c(
            "pe_vs_industry",
            "P/E 40%-60% below the industry's",
            "P/E / industry P/E, a band 0.4 .. 0.6 (screener, current)",
            ">=",
            PE_LOW,
            "a band, both ends included (decided 2026-11-07); P/E <= 0 fails; no industry P/E = NA",
        ),
        _c(
            "price_in_range",
            "Price in the lower half of the 52-week range",
            "(price - 52-week low) / (52-week high - 52-week low)",
            "<",
            RANGE_MIDDLE,
            "below the middle of the range, as in the summary (N2); shows the multiple is low "
            "because the price fell",
        ),
        _c(
            "eps_growth",
            "EPS growth between 7% and 22%",
            "EPS growth over 5 years (%): the screener's figure, else CAGR of EPS (Diluted)",
            ">=",
            EPS_GROWTH_LOW,
            "a band 7 .. 22, both ends included; too much growth is as suspect as too little (N3)",
        ),
        _c(
            "total_return",
            "Total return twice the industry's",
            "(EPS growth + dividend yield) / P/E  >=  2 x the industry median of the same figure",
            ">=",
            TOTAL_RETURN_FACTOR,
            "value = the stock's figure, threshold = 2 x industry median (N4); the median is "
            "over all screener stocks of the industry with a positive P/E (at least 5)",
        ),
        _c(
            "revenue_vs_eps",
            "Revenue growth at least 70% of EPS growth",
            "Revenue growth / EPS growth, both over 5 years (%)",
            ">=",
            ORGANIC_MIN,
            "organic growth; NA when EPS growth <= 0 (N5)",
        ),
        _c(
            "fcf_per_share",
            "Free cash flow per share positive",
            "Free Cash Flow Per Share, current (TTM, else latest FY) > 0",
            ">",
            0.0,
            "the same test as lesson 5",
        ),
        _c(
            "momentum",
            "Each of the last 4 quarters above the same quarter a year earlier",
            "EPS (Diluted) of each of the 4 latest fiscal quarters > EPS of the same quarter "
            "one year before",
            ">=",
            float(QUARTERS),
            "value = quarters that improved; each quarter on its own, as the summary says (N8)",
        ),
    )
}


def _band(criterion: Criterion, value: float | None, low: float, high: float, note=None) -> Result:
    """Both ends included; strength is the worse of the two sides (as Fisher's R&D band)."""
    if is_missing(value):
        return evaluate(criterion, None, note)
    value = round(value, 9)
    passed = low <= value <= high
    score = min(strength(value, low, ">="), strength(value, high, "<="))
    return Result(
        GURU, criterion.id, Status.PASS if passed else Status.FAIL, value, None, score, note
    )


def _pe_vs_industry(pe: float | None, industry_pe: float | None) -> Result:
    c = CRITERIA["pe_vs_industry"]
    if is_missing(industry_pe) or industry_pe <= 0 or is_missing(pe):
        return evaluate(c, None, "no industry P/E or no P/E")
    if pe <= 0:
        return Result(GURU, c.id, Status.FAIL, None, None, 0.0, "P/E <= 0")
    return _band(c, pe / industry_pe, PE_LOW, PE_HIGH)


def _price_in_range(price: float | None, low: float | None, high: float | None) -> Result:
    c = CRITERIA["price_in_range"]
    if any(is_missing(v) for v in (price, low, high)) or high <= low:
        return evaluate(c, None, "no price or no 52-week range")
    return evaluate(c, (price - low) / (high - low))


def _total_return(
    growth: float | None, dividend: float | None, pe: float | None, industry_median: float | None
) -> Result:
    c = CRITERIA["total_return"]
    if any(is_missing(v) for v in (growth, dividend, pe)) or pe <= 0:
        return evaluate(c, None, "no EPS growth, dividend yield or positive P/E")
    if is_missing(industry_median) or industry_median <= 0:
        return Result(GURU, c.id, Status.NA, None, None, None, "no industry median to compare with")
    value = (growth + dividend) / pe
    limit = TOTAL_RETURN_FACTOR * industry_median
    return evaluate(Criterion(**{**c.__dict__, "threshold": limit}), value)


def _revenue_vs_eps(revenue_growth: float | None, eps_growth: float | None) -> Result:
    c = CRITERIA["revenue_vs_eps"]
    if is_missing(revenue_growth) or is_missing(eps_growth):
        return evaluate(c, None)
    if eps_growth <= 0:
        return evaluate(c, None, "EPS growth <= 0: the ratio has no meaning")
    return evaluate(c, revenue_growth / eps_growth)


def _momentum(s: Statements) -> Result:
    c = CRITERIA["momentum"]
    latest = s.latest_quarters(rows.EPS_DILUTED, QUARTERS)
    if len(latest) < QUARTERS:
        return evaluate(c, None, "fewer than 4 quarters")
    improved = 0
    for year, q in latest:
        now, before = s.quarter(rows.EPS_DILUTED, year, q), s.quarter(rows.EPS_DILUTED, year - 1, q)
        if is_missing(before):
            return evaluate(c, None, f"no EPS for Q{q} {year - 1}")
        improved += now > before
    passed = improved == QUARTERS
    score = 1.0 if passed else (0.25 if improved == QUARTERS - 1 else 0.0)
    return Result(
        GURU, c.id, Status.PASS if passed else Status.FAIL, float(improved), c.threshold, score
    )


def evaluate_neff(
    s: Statements,
    *,
    pe: float | None,
    industry_pe: float | None,
    price: float | None,
    low_52: float | None,
    high_52: float | None,
    eps_growth_5y: float | None,
    revenue_growth_5y: float | None,
    dividend_yield: float | None,
    industry_return_median: float | None,
) -> list[Result]:
    """All of lesson 8 for one stock. The growth figures are the screener's own (their window
    reaches years the free statement pages hide); only a missing one falls back to a CAGR."""
    c = CRITERIA
    eps_g = eps_growth_5y
    if is_missing(eps_g):
        eps_g = cagr_pct(s.series(rows.EPS_DILUTED, 5))
    revenue_g = revenue_growth_5y
    if is_missing(revenue_g):
        revenue_g = cagr_pct(s.series(rows.REVENUE, 5))
    eps_note = "screener value (5-year window)" if not is_missing(eps_growth_5y) else (
        "computed from 5 fiscal years"
    )
    return [
        _pe_vs_industry(pe, industry_pe),
        _price_in_range(price, low_52, high_52),
        _band(c["eps_growth"], eps_g, EPS_GROWTH_LOW, EPS_GROWTH_HIGH, eps_note),
        _total_return(eps_g, dividend_yield, pe, industry_return_median),
        _revenue_vs_eps(revenue_g, eps_g),
        evaluate(c["fcf_per_share"], fcf_per_share(s)),
        _momentum(s),
    ]
