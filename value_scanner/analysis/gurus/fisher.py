"""Lesson 5 - Ken Fisher's six criteria (C5), as in the lesson PDF (decisions D1, D3, D4).

Variants NOT implemented (ROADMAP D3): the "super stock" 0.4 label and the sector exceptions
(technology: P/E and P/OCF instead of P/S; industrials: P/E and Graham number). The P/S limit
is a parameter chosen by the classifier: 0.8 for cyclical companies, 1.5 otherwise.
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
from value_scanner.analysis.statements import Statements

GURU = "fisher"
PS_CYCLICAL, PS_OTHER = 0.8, 1.5
RD_LOW, RD_HIGH = 5.0, 15.0

CRITERIA = {
    c.id: c
    for c in (
        Criterion(
            "ps",
            GURU,
            5,
            "Price / sales",
            "P/S (screener, current)",
            "<",
            PS_OTHER,
            "limit 0.8 for cyclical companies, 1.5 otherwise; P/S <= 0 fails",
        ),
        Criterion(
            "eps_growth",
            GURU,
            5,
            "EPS growth, 5-year average",
            "mean of the 4 year-over-year growths of EPS (Diluted) over 5 FY (%)",
            ">",
            15.0,
            "NA if any year's base EPS is not positive",
        ),
        Criterion(
            "net_margin",
            GURU,
            5,
            "Net margin, 5-year average",
            "mean over FYs of Net Income / Revenue (%), >= 3 valid years",
            ">",
            5.0,
            "D1: 5% (PDF) rather than the 8%/15% sector variant",
        ),
        Criterion(
            "debt_equity",
            GURU,
            5,
            "Liabilities / equity",
            "Total Liabilities / Shareholders' Equity, current",
            "<",
            0.4,
            "equity <= 0 fails. Lesson 5's formula sheet says total liabilities",
        ),
        Criterion(
            "fcf",
            GURU,
            5,
            "Positive free cash flow per share",
            "Free Cash Flow per share, current",
            ">",
            0.0,
        ),
        Criterion(
            "rd",
            GURU,
            5,
            "Market cap / R&D between 5 and 15",
            "market cap (USD millions) / Research & Development, latest FY",
            ">=",
            RD_LOW,
            "band: 5 <= ratio <= 15. Technology and pharma only; NA elsewhere (D4)",
        ),
    )
}


def _yoy_growth_avg_pct(values: list[float | None]) -> float | None:
    """Mean year-over-year growth of a newest-first series; None unless every base is positive."""
    growths = []
    for new, old in zip(values[:-1], values[1:], strict=True):
        if is_missing(new) or is_missing(old) or old <= 0:
            return None
        growths.append((new / old - 1) * 100)
    return sum(growths) / len(growths) if growths else None


def _avg_net_margin_pct(s: Statements) -> float | None:
    margins = []
    for n in range(5):
        income, revenue = s.fy(rows.NET_INCOME, n), s.fy(rows.REVENUE, n)
        if is_missing(income) or is_missing(revenue) or revenue <= 0:
            continue
        margins.append(income / revenue * 100)
    return sum(margins) / len(margins) if len(margins) >= 3 else None


def fcf_per_share(s: Statements) -> float | None:
    value = s.current("Free Cash Flow Per Share")
    if not is_missing(value):
        return value
    fcf, shares = s.current(rows.FREE_CASH_FLOW), s.current(rows.SHARES_DILUTED)
    return None if is_missing(fcf) or is_missing(shares) or shares <= 0 else fcf / shares


def _rd_band(s: Statements, market_cap: float | None, applies: bool) -> Result:
    c = CRITERIA["rd"]
    if not applies:
        return Result(GURU, c.id, Status.NA, None, None, None, "not a technology/pharma company")
    rd = s.fy(rows.RESEARCH_AND_DEVELOPMENT, 0)
    if is_missing(market_cap) or is_missing(rd) or rd <= 0:
        return Result(GURU, c.id, Status.NA, None, None, None, "no market cap or R&D data")
    ratio = round(market_cap / 1e6 / rd, 9)
    passed = RD_LOW <= ratio <= RD_HIGH
    score = min(strength(ratio, RD_LOW, ">="), strength(ratio, RD_HIGH, "<="))
    return Result(
        GURU,
        c.id,
        Status.PASS if passed else Status.FAIL,
        ratio,
        None,
        score,
        "threshold band 5..15",
    )


def evaluate_fisher(
    s: Statements,
    ps: float | None,
    market_cap: float | None,
    *,
    cyclical: bool = False,
    rd_applies: bool = False,
) -> list[Result]:
    c = CRITERIA
    ps_limit = PS_CYCLICAL if cyclical else PS_OTHER
    ps_criterion = Criterion(**{**c["ps"].__dict__, "threshold": ps_limit})
    if not is_missing(ps) and ps <= 0:
        ps_result = Result(GURU, "ps", Status.FAIL, ps, ps_limit, 0.0, "P/S <= 0")
    else:
        ps_result = evaluate(ps_criterion, ps)

    equity = s.current(rows.EQUITY)
    liabilities = s.current(rows.TOTAL_LIABILITIES)
    if not is_missing(equity) and equity <= 0:
        de = Result(GURU, "debt_equity", Status.FAIL, None, 0.4, 0.0, "shareholders' equity <= 0")
    else:
        ratio = None if is_missing(liabilities) or is_missing(equity) else liabilities / equity
        de = evaluate(c["debt_equity"], ratio)

    return [
        ps_result,
        evaluate(c["eps_growth"], _yoy_growth_avg_pct(s.series(rows.EPS_DILUTED, 5))),
        evaluate(c["net_margin"], _avg_net_margin_pct(s)),
        de,
        evaluate(c["fcf"], fcf_per_share(s)),
        _rd_band(s, market_cap, rd_applies),
    ]
