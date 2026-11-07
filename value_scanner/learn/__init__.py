"""Plain-language explanations for every line of the financial statements (the learning page)."""

from __future__ import annotations

from dataclasses import dataclass

from value_scanner.learn.items_balance import BALANCE
from value_scanner.learn.items_cashflow import CASHFLOW
from value_scanner.learn.items_income import INCOME

STATEMENT_ITEMS = {"income": INCOME, "balance_sheet": BALANCE, "cash_flow": CASHFLOW}

# Rows shown in bold, like StockAnalysis's totals and sub-totals.
TOTALS = frozenset(
    {
        "Revenue",
        "Gross Profit",
        "Operating Income",
        "Pretax Income",
        "Net Income",
        "EPS (Diluted)",
        "EBITDA",
        "Total Current Assets",
        "Total Assets",
        "Total Current Liabilities",
        "Total Liabilities",
        "Shareholders' Equity",
        "Total Liabilities & Equity",
        "Operating Cash Flow",
        "Investing Cash Flow",
        "Financing Cash Flow",
        "Net Cash Flow",
        "Free Cash Flow",
    }
)


@dataclass(frozen=True)
class Explanation:
    he: str
    short: str
    how: str = ""
    look: str = ""


def explain(statement: str, item: str) -> Explanation | None:
    entry = STATEMENT_ITEMS.get(statement, {}).get(item)
    if entry is None:
        return None
    return Explanation(*(list(entry) + ["", "", ""])[:4])


def kind(item: str) -> str:
    """How the row is drawn: percent rows are italic, totals bold."""
    if item.endswith("(%)") or item.endswith("Growth") or "Growth" in item:
        return "pct"
    return "total" if item in TOTALS else "normal"
