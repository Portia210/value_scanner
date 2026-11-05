"""Lesson 4 - Benjamin Graham's six criteria (C4).

P/E and P/B are the screener's *current* values (today's price). Statement amounts are in
millions of the reporting currency (for foreign filers that is not USD: open item P12).
"""

from __future__ import annotations

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import Criterion, Result, Status, evaluate, is_missing
from value_scanner.analysis.debt import long_term_debt
from value_scanner.analysis.statements import Statements

GURU = "graham"
DEFAULT_PE_LIMIT = 15.0  # technology may use 25 (decisions D5/D6, chosen by the classifier)

CRITERIA = {
    c.id: c
    for c in (
        Criterion(
            "sales",
            GURU,
            4,
            "Sales above $350M",
            "Revenue, latest FY (millions)",
            ">",
            350.0,
            "reporting currency, not converted",
        ),
        Criterion(
            "current_ratio",
            GURU,
            4,
            "Current ratio above 2",
            "Total Current Assets / Total Current Liabilities, current",
            ">",
            2.0,
        ),
        Criterion(
            "working_capital",
            GURU,
            4,
            "Working capital above long-term debt",
            "(Total Current Assets - Total Current Liabilities) - Long-Term Debt, current",
            ">",
            0.0,
            "no Long-Term Debt row = no long-term debt (0), if the balance sheet exists",
        ),
        Criterion(
            "pe",
            GURU,
            4,
            "P/E below 15",
            "price / EPS (screener, current)",
            "<",
            DEFAULT_PE_LIMIT,
            "P/E <= 0 fails; the limit is 25 for technology (D5)",
        ),
        Criterion(
            "graham_number",
            GURU,
            4,
            "P/E x P/B below 22",
            "P/E x P/B (screener, current)",
            "<",
            22.0,
            "either factor <= 0 fails",
        ),
        Criterion(
            "eps_growth",
            GURU,
            4,
            "EPS growth above 30%, no loss year",
            "mean(EPS last 2 FY) / mean(EPS first 2 of 5 FY) - 1 (%); any FY EPS < 0 fails",
            ">",
            30.0,
            "needs 5 fiscal years of EPS",
        ),
    )
}


def _positive_multiple(criterion: Criterion, value: float | None, label: str) -> Result:
    """A multiple that must be below a limit: negative or zero is a failure, not a pass."""
    if not is_missing(value) and value <= 0:
        return Result(
            GURU, criterion.id, Status.FAIL, value, criterion.threshold, 0.0, f"{label} <= 0"
        )
    return evaluate(criterion, value)


def _eps_growth(s: Statements) -> Result:
    c = CRITERIA["eps_growth"]
    eps = s.series(rows.EPS_DILUTED, 5)
    if any(not is_missing(v) and v < 0 for v in eps):
        return Result(GURU, c.id, Status.FAIL, None, c.threshold, 0.0, "a loss year in 5 FY")
    if any(is_missing(v) for v in eps):
        return evaluate(c, None, "needs 5 fiscal years of EPS")
    base = (eps[3] + eps[4]) / 2
    if base <= 0:
        return evaluate(c, None, "base-period EPS is not positive")
    return evaluate(c, ((eps[0] + eps[1]) / 2 / base - 1) * 100)


def _working_capital_vs_debt(s: Statements) -> Result:
    c = CRITERIA["working_capital"]
    assets = s.current(rows.TOTAL_CURRENT_ASSETS)
    liabilities = s.current(rows.TOTAL_CURRENT_LIABILITIES)
    if is_missing(assets) or is_missing(liabilities):
        return evaluate(c, None)
    long_term = long_term_debt(s.current)
    if long_term is None:
        return evaluate(c, None, "no balance sheet")
    return evaluate(c, assets - liabilities - long_term, "working capital minus long-term debt")


def evaluate_graham(
    s: Statements, pe: float | None, pb: float | None, pe_limit: float = DEFAULT_PE_LIMIT
) -> list[Result]:
    c = CRITERIA
    pe_criterion = Criterion(**{**c["pe"].__dict__, "threshold": pe_limit})
    product = None if is_missing(pe) or is_missing(pb) else pe * pb
    if not is_missing(pe) and not is_missing(pb) and (pe <= 0 or pb <= 0):
        graham = Result(GURU, "graham_number", Status.FAIL, product, 22.0, 0.0, "P/E or P/B <= 0")
    else:
        graham = evaluate(c["graham_number"], product)
    current_ratio = None
    ca, cl = s.current(rows.TOTAL_CURRENT_ASSETS), s.current(rows.TOTAL_CURRENT_LIABILITIES)
    if not is_missing(ca) and not is_missing(cl) and cl > 0:
        current_ratio = ca / cl
    return [
        evaluate(c["sales"], s.fy(rows.REVENUE, 0)),
        evaluate(c["current_ratio"], current_ratio),
        _working_capital_vs_debt(s),
        _positive_multiple(pe_criterion, pe, "P/E"),
        graham,
        _eps_growth(s),
    ]
