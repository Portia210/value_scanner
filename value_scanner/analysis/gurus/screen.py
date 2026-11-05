"""Lesson 3 - the initial screen (C3): eight questions every candidate must answer.

Market cap and P/E are *current* values from the screener (the price of today); the six
ratios are computed from the statements so that every number has a visible formula.
"""

from __future__ import annotations

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import Criterion, Result, Status, evaluate, is_missing
from value_scanner.analysis.statements import Statements

GURU = "screen"
MIN_ROE_YEARS = 3  # fiscal years needed for the 5-year ROE average

CRITERIA = {
    c.id: c
    for c in (
        Criterion("market_cap", GURU, 3, "Market cap", "market cap (screener, USD)", ">", 2e9),
        Criterion(
            "pe",
            GURU,
            3,
            "P/E",
            "price / EPS (screener, current price)",
            ">",
            5.0,
            "lower bound only: a very low P/E is a warning sign (lesson 3)",
        ),
        Criterion(
            "revenue_growth_5y",
            GURU,
            3,
            "Revenue growth, 5 years",
            "CAGR of Revenue, latest FY vs 4 FYs earlier (%)",
            ">",
            0.0,
        ),
        Criterion(
            "profit_margin",
            GURU,
            3,
            "Net profit margin",
            "Net Income / Revenue, current (TTM) (%)",
            ">",
            8.0,
        ),
        Criterion(
            "eps_growth_5y",
            GURU,
            3,
            "EPS growth, 5 years",
            "CAGR of EPS (Diluted), latest FY vs 4 FYs earlier (%)",
            ">",
            0.0,
            "NA when the base year EPS is not positive",
        ),
        Criterion(
            "debt_equity",
            GURU,
            3,
            "Debt / equity",
            "Total Debt / Shareholders' Equity, current",
            "<",
            0.5,
            "equity <= 0 fails (debt with no owners' capital)",
        ),
        Criterion(
            "current_ratio",
            GURU,
            3,
            "Current ratio",
            "Total Current Assets / Total Current Liabilities, current",
            ">",
            2.0,
        ),
        Criterion(
            "roe_5y",
            GURU,
            3,
            "Return on equity, 5-year average",
            "mean over FYs of Net Income / Shareholders' Equity (%), >= 3 valid years",
            ">",
            10.0,
            "years with equity <= 0 are skipped",
        ),
    )
}


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if is_missing(numerator) or is_missing(denominator) or denominator == 0:
        return None
    return numerator / denominator


def cagr_pct(series: list[float | None]) -> float | None:
    """Compound growth in % between the newest and the oldest value of a newest-first series
    (needs both ends; both must be positive, otherwise the rate is not meaningful -> None)."""
    if len(series) < 2:
        return None
    new, old = series[0], series[-1]
    if is_missing(new) or is_missing(old) or new <= 0 or old <= 0:
        return None
    return ((new / old) ** (1 / (len(series) - 1)) - 1) * 100


def roe_5y_avg_pct(s: Statements) -> float | None:
    values = []
    for n in range(5):
        income, equity = s.fy(rows.NET_INCOME, n), s.fy(rows.EQUITY, n)
        if is_missing(income) or is_missing(equity) or equity <= 0:
            continue
        values.append(income / equity * 100)
    return sum(values) / len(values) if len(values) >= MIN_ROE_YEARS else None


def _prefer_screener(
    criterion: Criterion, screener: float | None, computed: float | None
) -> Result:
    """The screener's own 5-year figure (its window reaches years the free statement pages hide)
    decides; the figure computed from our 5 fiscal years is only a fallback."""
    if not is_missing(screener):
        return evaluate(criterion, screener, "screener value (5-year window)")
    return evaluate(criterion, computed, "computed from 5 fiscal years")


def evaluate_screen(
    s: Statements,
    market_cap: float | None,
    pe: float | None,
    *,
    revenue_growth_5y: float | None = None,
    eps_growth_5y: float | None = None,
    roe_5y: float | None = None,
) -> list[Result]:
    c = CRITERIA
    margin = _ratio(s.current(rows.NET_INCOME), s.current(rows.REVENUE))
    equity = s.current(rows.EQUITY)
    debt_equity = _ratio(s.current(rows.TOTAL_DEBT), equity)

    if not is_missing(equity) and equity <= 0:
        de_result = Result(
            GURU,
            "debt_equity",
            Status.FAIL,
            None,
            c["debt_equity"].threshold,
            0.0,
            "shareholders' equity <= 0",
        )
    else:
        de_result = evaluate(c["debt_equity"], debt_equity)

    return [
        evaluate(c["market_cap"], market_cap),
        evaluate(c["pe"], pe),
        _prefer_screener(
            c["revenue_growth_5y"], revenue_growth_5y, cagr_pct(s.series(rows.REVENUE, 5))
        ),
        evaluate(c["profit_margin"], None if margin is None else margin * 100),
        _prefer_screener(
            c["eps_growth_5y"], eps_growth_5y, cagr_pct(s.series(rows.EPS_DILUTED, 5))
        ),
        de_result,
        evaluate(
            c["current_ratio"],
            _ratio(s.current(rows.TOTAL_CURRENT_ASSETS), s.current(rows.TOTAL_CURRENT_LIABILITIES)),
        ),
        _prefer_screener(c["roe_5y"], roe_5y, roe_5y_avg_pct(s)),
    ]
