"""Long-term debt for Graham (working capital vs long-term debt) and Piotroski.

Rule (developer, 2026-11-06): a balance sheet without a `Long-Term Debt` row means the company
has no long-term debt -> 0. If the balance sheet itself is missing (no Total Assets), the
answer is unknown -> None, never 0. No other formula is substituted.
"""

from __future__ import annotations

from collections.abc import Callable

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import is_missing

Getter = Callable[[str], float | None]


def long_term_debt(get: Getter) -> float | None:
    value = get(rows.LONG_TERM_DEBT)
    if not is_missing(value):
        return value
    return 0.0 if not is_missing(get(rows.TOTAL_ASSETS)) else None
