"""Lesson 7 - Warren Buffett (C11): quality first, numbers second, price last.

The lesson has three stages: qualitative parameters, quantitative parameters, and an attractive
price found "only by DCF". Only the six quantitative tests can be computed from the statements.
The qualitative parameters and the DCF price stay in the table as human checks (status MANUAL):
they never count in a score or in the coverage.

Every reading the lesson leaves open is listed in docs/formula-decisions.md (items B1-B8).
"""

from __future__ import annotations

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import (
    Criterion,
    Result,
    Status,
    evaluate,
    is_missing,
    manual_result,
)
from value_scanner.analysis.gurus.screen import prefer_screener, roe_5y_avg_pct
from value_scanner.analysis.statements import Statements

GURU = "buffett"
YEARS = 5
RETAINED_EARNINGS_GROWTH_PCT = 12.0
ROA_PCT = 12.0
ROE_PCT = 15.0


def _manual(cid: str, title: str, formula: str) -> Criterion:
    return Criterion(
        cid, GURU, 7, title, formula, ">", 0.0, "a person decides; not part of any score", True
    )


CRITERIA = {
    c.id: c
    for c in (
        _manual(
            "consumer_monopoly",
            "Position: a consumer monopoly",
            "Could someone with billions and the best managers build a competitor? "
            "Brand, patents, must-have product, essential service (lesson 7)",
        ),
        _manual(
            "inflation_pricing",
            "Can raise prices with inflation",
            "Did the product price rise over one or two decades without losing market share?",
        ),
        _manual(
            "simple_product",
            "Simple product and business model",
            "Is the product easy to understand, with a clear business model?",
        ),
        Criterion(
            "eps_growth",
            GURU,
            7,
            "EPS grew every year, no loss year",
            "EPS (Diluted) higher than the year before in each step over 5 FY (4 steps), "
            "and Net Income > 0 in all 5 FY",
            ">=",
            4.0,
            "value = number of yearly increases; NA with fewer than 5 fiscal years (B1)",
        ),
        Criterion(
            "earnings_vs_liabilities",
            GURU,
            7,
            "5-year net income above long-term liabilities",
            "sum of Net Income over 5 FY > Total Liabilities - Total Current Liabilities "
            "(latest FY)",
            ">",
            0.0,
            "long-term liabilities is a derived figure, not a row of the site (B2); "
            "threshold = the liabilities; not applicable to financial companies",
        ),
        Criterion(
            "roe_5y",
            GURU,
            7,
            "Return on equity, 5-year average",
            "mean over FYs of Net Income / Shareholders' Equity (%), >= 3 valid years",
            ">",
            ROE_PCT,
            "the same figure as lesson 3 with a stricter threshold (15% instead of 10%)",
        ),
        Criterion(
            "roa",
            GURU,
            7,
            "Return on assets, last year",
            "Net Income / Total Assets, latest FY (%)",
            ">",
            ROA_PCT,
            "a high bar (B5); on year-end assets",
        ),
        Criterion(
            "retained_earnings",
            GURU,
            7,
            "Earnings growth relative to retained earnings",
            "(Net Income FY0 - Net Income FY1) / Retained Earnings FY0 (%)",
            ">=",
            RETAINED_EARNINGS_GROWTH_PCT,
            "OPEN (B3): one-year change, as the PDF says; retained earnings <= 0 fails",
        ),
        Criterion(
            "fcf",
            GURU,
            7,
            "Free cash flow positive, last year",
            "Free Cash Flow, latest FY > 0",
            ">",
            0.0,
            "OPEN (B4): last year, as the PDF says (the summary says a 5-year average)",
        ),
        _manual(
            "dcf_price",
            "Attractive price by DCF",
            "Buffett prices a company only by discounted cash flow; the lesson gives no "
            "discount rate, horizon or terminal value",
        ),
    )
}


def _eps_growth(s: Statements) -> Result:
    c = CRITERIA["eps_growth"]
    eps = [s.fy(rows.EPS_DILUTED, n) for n in range(YEARS)]
    income = [s.fy(rows.NET_INCOME, n) for n in range(YEARS)]
    if any(is_missing(v) for v in eps + income):
        return Result(GURU, c.id, Status.NA, None, c.threshold, None, "fewer than 5 fiscal years")
    steps = sum(1 for n in range(YEARS - 1) if eps[n] > eps[n + 1])  # newest first
    profitable = all(v > 0 for v in income)
    passed = steps == YEARS - 1 and profitable
    near = steps >= YEARS - 2 and profitable
    score = 1.0 if passed else (0.25 if near else 0.0)
    note = None if profitable else "a loss year"
    status = Status.PASS if passed else Status.FAIL
    return Result(GURU, c.id, status, float(steps), c.threshold, score, note)


def _earnings_vs_liabilities(s: Statements) -> Result:
    c = CRITERIA["earnings_vs_liabilities"]
    incomes = [s.fy(rows.NET_INCOME, n) for n in range(YEARS)]
    total, current = s.fy(rows.TOTAL_LIABILITIES, 0), s.fy(rows.TOTAL_CURRENT_LIABILITIES, 0)
    if any(is_missing(v) for v in incomes) or is_missing(total) or is_missing(current):
        return Result(GURU, c.id, Status.NA, None, None, None, "missing years or liabilities")
    long_term = total - current
    if long_term < 0:
        return Result(GURU, c.id, Status.NA, None, None, None, "current liabilities exceed total")
    return evaluate(Criterion(**{**c.__dict__, "threshold": long_term}), sum(incomes))


def _roa(s: Statements) -> Result:
    income, assets = s.fy(rows.NET_INCOME, 0), s.fy(rows.TOTAL_ASSETS, 0)
    if is_missing(income) or is_missing(assets) or assets <= 0:
        return evaluate(CRITERIA["roa"], None)
    return evaluate(CRITERIA["roa"], income / assets * 100)


def _retained_earnings(s: Statements) -> Result:
    c = CRITERIA["retained_earnings"]
    now, before = s.fy(rows.NET_INCOME, 0), s.fy(rows.NET_INCOME, 1)
    retained = s.fy(rows.RETAINED_EARNINGS, 0)
    if is_missing(now) or is_missing(before) or is_missing(retained):
        return evaluate(c, None)
    if retained <= 0:
        return Result(
            GURU, c.id, Status.FAIL, None, c.threshold, 0.0, "retained earnings <= 0 (deficit)"
        )
    return evaluate(c, (now - before) / retained * 100)


def _fcf(s: Statements) -> Result:
    return evaluate(CRITERIA["fcf"], s.fy(rows.FREE_CASH_FLOW, 0))


def evaluate_buffett(s: Statements, roe_5y: float | None = None) -> list[Result]:
    """All of lesson 7 for one stock, in table order. `roe_5y` is the screener's own 5-year figure
    (preferred, as in lesson 3); without it the average is computed from the fiscal years."""
    return [
        manual_result(CRITERIA["consumer_monopoly"]),
        manual_result(CRITERIA["inflation_pricing"]),
        manual_result(CRITERIA["simple_product"]),
        _eps_growth(s),
        _earnings_vs_liabilities(s),
        prefer_screener(CRITERIA["roe_5y"], roe_5y, roe_5y_avg_pct(s)),
        _roa(s),
        _retained_earnings(s),
        _fcf(s),
        manual_result(CRITERIA["dcf_price"]),
    ]
