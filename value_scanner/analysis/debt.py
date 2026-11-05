"""Long-term debt when the page has no `Long-Term Debt` row (about half of the companies).

Fallback: Total Debt minus its current parts (current portion of long-term debt, short-term
debt, current portion of leases) - i.e. long-term debt plus long-term leases. Total Debt itself
missing -> None (unknown, never 0).
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
    total = get(rows.TOTAL_DEBT)
    if is_missing(total):
        return None
    current = sum(
        v
        for item in (rows.CURRENT_PORTION_LTD, rows.SHORT_TERM_DEBT, rows.CURRENT_PORTION_LEASES)
        if not is_missing(v := get(item))
    )
    return max(total - current, 0.0)
