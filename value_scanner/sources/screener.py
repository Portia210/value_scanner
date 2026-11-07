"""The stock universe from StockAnalysis's screener JSON (D7, B3).

Two requests give every listed stock, its current price and the lesson-3 filter fields; the
8 initial-screen filters are applied here in code (verified: 109 matches = the saved screen).
No login and no browser. A Cloudflare challenge is reported as `Blocked` and is never bypassed.
"""

from __future__ import annotations

import operator
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

BASE = "https://stockanalysis.com"
INITIAL_PATH = "/_api/endpoints/screener/initial?type=stock&countryCode=&format=compact"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE}/stocks/screener/",
}

# Lesson 3, initial screen. field -> (comparison, threshold); a missing value never passes.
FILTERS: dict[str, tuple[str, float]] = {
    "marketCap": (">", 2e9),
    "peRatio": (">", 5),
    "revenueGrowth5Y": (">", 0),
    "profitMargin": (">", 8),
    "epsGrowth5Y": (">", 0),
    "debtEquity": ("<", 0.5),
    "currentRatio": (">", 2),
    "roe5y": (">", 10),
}
_OPS: dict[str, Callable[[float, float], bool]] = {">": operator.gt, "<": operator.lt}

# Data points requested besides the filter fields.
EXTRA_FIELDS = (
    "country",
    "sector",
    "industry",
    "exchange",
    "price",
    "priceDate",
    "psRatio",
    "pbRatio",
    "pOcfRatio",
    "peRatio5Y",
    "lastEarningsDate",
    "nextEarningsDate",
    "lastReportDate",  # R5: period end of the latest financial report
    # Lesson 8 (Neff): industry P/E, the 52-week range, dividend yield (percent)
    "industryPe",
    "low52",
    "high52",
    "dividendYield",
)
DATA_POINT_IDS = (*FILTERS, *EXTRA_FIELDS)

# A filter field that is non-null for fewer stocks than this means the JSON changed shape
# (on 2026-11-05 the sparsest, epsGrowth5Y, was 36%).
MIN_FIELD_COVERAGE = 0.15
# Fewer stocks than this share of the previous run is treated as a structure change.
MIN_UNIVERSE_RATIO = 0.7
# A stock failing at most this many filters is stored as "almost" (screener_snapshots).
ALMOST_MAX_FAILED = 2


class Blocked(RuntimeError):
    """Cloudflare (or the site) refused the request. Wait and retry later; never work around."""


class StructureChanged(RuntimeError):
    """The JSON no longer has the shape the code expects."""


@dataclass(frozen=True)
class ScreenerStock:
    symbol: str
    name: str | None
    volume: float | None
    values: Mapping[str, Any]  # data-point id -> value

    def get(self, key: str) -> Any:
        return self.values.get(key)


@dataclass(frozen=True)
class FilterOutcome:
    passed: bool
    failed: tuple[str, ...]  # filters not passed (including those with a missing value)
    missing: tuple[str, ...]  # subset of `failed` that failed only because the value is missing


@dataclass
class Universe:
    stocks: dict[str, ScreenerStock]


def evaluate(stock: ScreenerStock) -> FilterOutcome:
    failed, missing = [], []
    for name, (op, threshold) in FILTERS.items():
        value = stock.get(name)
        if value is None:
            failed.append(name)
            missing.append(name)
        elif not _OPS[op](value, threshold):
            failed.append(name)
    return FilterOutcome(not failed, tuple(failed), tuple(missing))


def dedupe_share_classes(stocks: Iterable[ScreenerStock]) -> tuple[list[ScreenerStock], list[str]]:
    """D14: of several symbols with the same company name (GOOG/GOOGL, HEI/HEI.A) keep the one
    with the highest volume. Returns (kept, dropped symbols)."""
    groups: dict[str, list[ScreenerStock]] = defaultdict(list)
    for s in stocks:
        groups[(s.name or s.symbol).strip().casefold()].append(s)
    kept, dropped = [], []
    for group in groups.values():
        group.sort(key=lambda s: (-(s.volume or 0), s.symbol))
        kept.append(group[0])
        dropped.extend(s.symbol for s in group[1:])
    return sorted(kept, key=lambda s: s.symbol), sorted(dropped)


# ── parsing and validation ──────────────────────────────────────────────────────────────────
def parse_universe(initial: Any, data_points: Any) -> Universe:
    """Combine the two responses. Raises StructureChanged when the shape is wrong."""
    try:
        data = initial["data"]
        columns, rows = data["columns"], data["rows"]
        sym_i, name_i = columns.index("s"), columns.index("n")
        vol_i = columns.index("volume") if "volume" in columns else None
        points = data_points["data"]["data"]
    except (KeyError, TypeError, ValueError) as exc:
        raise StructureChanged(f"unexpected screener JSON shape: {exc!r}") from exc
    if not rows or not points:
        raise StructureChanged("screener returned zero stocks")

    stocks: dict[str, ScreenerStock] = {}
    for row in rows:
        symbol = row[sym_i]
        values = points.get(symbol)
        if values is None:
            continue
        stocks[symbol] = ScreenerStock(
            symbol=symbol,
            name=row[name_i],
            volume=row[vol_i] if vol_i is not None else None,
            values=values,
        )
    if not stocks:
        raise StructureChanged("no symbol appears in both screener responses")

    problems = []
    for name in FILTERS:
        have = sum(1 for s in stocks.values() if s.get(name) is not None)
        share = have / len(stocks)
        if share < MIN_FIELD_COVERAGE:
            problems.append(f"field {name} is present for only {share:.0%} of stocks")
    if problems:
        raise StructureChanged("; ".join(problems))
    return Universe(stocks)


# ── network ─────────────────────────────────────────────────────────────────────────────────
def _check(resp: httpx.Response) -> httpx.Response:
    challenged = bool(resp.headers.get("cf-mitigated")) or "Just a moment" in resp.text[:2000]
    if resp.status_code in (403, 429, 503) or challenged:
        raise Blocked(f"HTTP {resp.status_code} from {resp.request.url.path}")
    resp.raise_for_status()
    return resp


def fetch_universe(
    client: httpx.Client | None = None,
    pause: float = 4.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Universe:
    """Two slow requests; returns the parsed Universe."""
    own = client is None
    client = client or httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True)
    try:
        initial = _check(client.get(BASE + INITIAL_PATH)).json()
        sleep(pause)
        # '+' separates ids and must reach the server literally, so build the URL by hand.
        ids_path = "/_api/endpoints/screener/data-points?type=s&ids=" + "+".join(DATA_POINT_IDS)
        points = _check(client.get(BASE + ids_path)).json()
    finally:
        if own:
            client.close()
    return parse_universe(initial, points)
