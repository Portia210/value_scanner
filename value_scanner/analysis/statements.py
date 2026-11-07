"""One stock's statements, loaded from the database, with year-aware accessors (C1)."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from value_scanner.storage.repo import Repository

_FY = re.compile(r"^FY (\d{4})$")
_QUARTER = re.compile(r"^Q([1-4]) (\d{4})$")
STATEMENTS = ("income", "balance_sheet", "cash_flow", "income_quarterly")


def _clean(value: float | None) -> float | None:
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else value


class Statements:
    """item -> period -> value, merged over the statements of one symbol.

    `fy(item, 0)` is the latest fiscal year, `fy(item, 1)` the one before; `ttm(item)` the
    trailing-twelve-months column; `current(item)` the TTM when present, else the latest FY.
    A missing item, period or value gives None (never 0).
    """

    def __init__(self, rows: Iterable[tuple[str, str, float | None]]):
        self._data: dict[str, dict[str, float | None]] = {}
        for item, period, value in rows:
            self._data.setdefault(item, {}).setdefault(period, _clean(value))

    @classmethod
    def from_repo(
        cls, repo: Repository, symbol: str, statements: Iterable[str] = STATEMENTS
    ) -> Statements:
        rows: list[tuple[str, str, float | None]] = []
        for statement in statements:
            fetch = repo.latest_statement_fetch(symbol, statement)
            if fetch is not None:
                rows.extend(
                    (r["item"], r["period"], r["value"]) for r in repo.statement_values(fetch["id"])
                )
        return cls(rows)

    def has(self, item: str) -> bool:
        return item in self._data

    def years(self, item: str | None = None) -> list[int]:
        """Fiscal years available (newest first), over all items or for one item."""
        items = [item] if item else list(self._data)
        found = {
            int(m.group(1)) for it in items for p in self._data.get(it, {}) if (m := _FY.match(p))
        }
        return sorted(found, reverse=True)

    def fy(self, item: str, n: int = 0) -> float | None:
        years = self.years()
        if n >= len(years):
            return None
        return self._data.get(item, {}).get(f"FY {years[n]}")

    def in_year(self, item: str, year: int) -> float | None:
        """The value of `item` for fiscal year `year` (None if missing)."""
        return self._data.get(item, {}).get(f"FY {year}")

    def ttm(self, item: str) -> float | None:
        return self._data.get(item, {}).get("TTM")

    def current(self, item: str) -> float | None:
        value = self.ttm(item)
        return value if value is not None else self.fy(item, 0)

    def quarter(self, item: str, year: int, q: int) -> float | None:
        """`item` in fiscal quarter `q` (1-4) of fiscal year `year` (None if missing)."""
        return self._data.get(item, {}).get(f"Q{q} {year}")

    def latest_quarters(self, item: str, count: int = 4) -> list[tuple[int, int]]:
        """The newest `count` fiscal quarters (year, q) the statements have for `item`, newest first
        (fewer if there are fewer). Only quarters with a value count."""
        found = {
            (int(m.group(2)), int(m.group(1)))
            for p, v in self._data.get(item, {}).items()
            if v is not None and (m := _QUARTER.match(p))
        }
        return sorted(found, reverse=True)[:count]

    def series(self, item: str, years: int = 5) -> list[float | None]:
        """Last `years` fiscal years, newest first; None where missing."""
        return [self.fy(item, n) for n in range(years)]
