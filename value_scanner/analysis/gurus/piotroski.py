"""Lesson 6 - Joseph Piotroski (C6): is the company improving? Each test compares the latest
fiscal year (FY0) with the one before (FY1); strength is 1 or 0 and equal is not better.

The lesson lists a pricing screen first (equity 20% below the market or sector). Decision D2:
only for financial companies, against the median P/B of the sector inside the scanned
universe. The caller supplies the sector median; without it that test is NA.
"""

from __future__ import annotations

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import Criterion, Result, Status, compare, is_missing
from value_scanner.analysis.debt import long_term_debt
from value_scanner.analysis.statements import Statements

GURU = "piotroski"
PB_DISCOUNT = 0.8  # P/B at least 20% below the sector median


def _c(cid: str, title: str, formula: str, note: str = "") -> Criterion:
    return Criterion(cid, GURU, 6, title, formula, ">", 0.0, note)


CRITERIA = {
    c.id: c
    for c in (
        _c(
            "pb_discount",
            "Equity cheap versus the sector",
            "P/B <= 0.8 x sector median P/B (financial companies only, D2)",
            "NA for non-financial companies or without a sector median",
        ),
        _c(
            "current_ratio",
            "Current ratio improved",
            "Total Current Assets / Total Current Liabilities: FY0 > FY1",
        ),
        _c(
            "lt_debt_assets",
            "Long-term debt / assets fell",
            "Long-Term Debt / Total Assets: FY0 < FY1",
            "no Long-Term Debt row = no long-term debt (0), if the balance sheet exists",
        ),
        _c(
            "cash_flow",
            "Operating cash flow positive and above net income",
            "Operating Cash Flow > 0 and > Net Income, FY0",
        ),
        _c(
            "roa",
            "Return on assets positive and higher",
            "Net Income / Total Assets: FY0 > 0 and FY0 > FY1",
        ),
        _c(
            "shares",
            "Fewer shares outstanding",
            "Shares Outstanding (Diluted): FY0 < FY1",
            "reported in millions, so a small buyback can round to equal (= fail)",
        ),
        _c("gross_margin", "Gross margin improved", "Gross Profit / Revenue: FY0 > FY1"),
        _c("asset_turnover", "Asset turnover improved", "Revenue / Total Assets: FY0 > FY1"),
    )
}


def _ratio(num: float | None, den: float | None) -> float | None:
    if is_missing(num) or is_missing(den) or den <= 0:
        return None
    return num / den


def _lt_debt(s: Statements, n: int) -> float | None:
    return long_term_debt(lambda item: s.fy(item, n))


def evaluate_piotroski(
    s: Statements,
    pb: float | None = None,
    sector_pb_median: float | None = None,
    pb_applies: bool = False,
) -> list[Result]:
    def ratio_pair(num_item: str, den_item: str) -> tuple[float | None, float | None]:
        return (
            _ratio(s.fy(num_item, 0), s.fy(den_item, 0)),
            _ratio(s.fy(num_item, 1), s.fy(den_item, 1)),
        )

    # pricing screen
    if not pb_applies or is_missing(pb) or is_missing(sector_pb_median) or sector_pb_median <= 0:
        why = "not a financial company" if not pb_applies else "no P/B or sector median"
        pricing = Result(GURU, "pb_discount", Status.NA, None, None, None, why)
    elif pb <= 0:
        pricing = Result(GURU, "pb_discount", Status.FAIL, pb, None, 0.0, "P/B <= 0")
    else:
        passed = round(pb / sector_pb_median, 9) <= PB_DISCOUNT
        pricing = Result(
            GURU,
            "pb_discount",
            Status.PASS if passed else Status.FAIL,
            pb / sector_pb_median,
            PB_DISCOUNT,
            1.0 if passed else 0.0,
        )

    cr_now = _ratio(s.fy(rows.TOTAL_CURRENT_ASSETS, 0), s.fy(rows.TOTAL_CURRENT_LIABILITIES, 0))
    cr_before = _ratio(s.fy(rows.TOTAL_CURRENT_ASSETS, 1), s.fy(rows.TOTAL_CURRENT_LIABILITIES, 1))

    debt_now = _ratio(_lt_debt(s, 0), s.fy(rows.TOTAL_ASSETS, 0))
    debt_before = _ratio(_lt_debt(s, 1), s.fy(rows.TOTAL_ASSETS, 1))

    ocf, income = s.fy(rows.OPERATING_CASH_FLOW, 0), s.fy(rows.NET_INCOME, 0)
    if is_missing(ocf) or is_missing(income):
        cash = Result(GURU, "cash_flow", Status.NA, ocf, income, None, "no data")
    else:
        ok = ocf > 0 and ocf > income
        cash = Result(
            GURU, "cash_flow", Status.PASS if ok else Status.FAIL, ocf, income, 1.0 if ok else 0.0
        )

    roa_now, roa_before = ratio_pair(rows.NET_INCOME, rows.TOTAL_ASSETS)
    roa = compare(GURU, "roa", roa_now, roa_before)
    if roa.status == Status.PASS and roa_now <= 0:  # improved, but still not positive
        roa = Result(GURU, "roa", Status.FAIL, roa_now, roa_before, 0.0, "return on assets <= 0")

    gm_now, gm_before = ratio_pair(rows.GROSS_PROFIT, rows.REVENUE)
    at_now, at_before = ratio_pair(rows.REVENUE, rows.TOTAL_ASSETS)
    return [
        pricing,
        compare(GURU, "current_ratio", cr_now, cr_before),
        compare(GURU, "lt_debt_assets", debt_now, debt_before, lower_is_better=True),
        cash,
        roa,
        compare(
            GURU,
            "shares",
            s.fy(rows.SHARES_DILUTED, 0),
            s.fy(rows.SHARES_DILUTED, 1),
            lower_is_better=True,
        ),
        compare(GURU, "gross_margin", gm_now, gm_before),
        compare(GURU, "asset_turnover", at_now, at_before),
    ]
