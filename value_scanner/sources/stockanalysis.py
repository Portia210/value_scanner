"""Financial statements from StockAnalysis.com pages (B1). Anonymous httpx, slow and bounded.

`parse_statement_table` turns the page's `table.financials-table` into long-format rows
(item, period, value). `StatementFetcher.fetch` downloads one page and classifies the outcome;
it never loops forever: network errors get a few bounded retries, a Cloudflare challenge or
429 is reported as "blocked" (no bypass), a missing table as "no_table".
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

BASE = "https://stockanalysis.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# statement key (statement_fetches.statement) -> path under /stocks/<symbol>/ (P14).
STATEMENT_PATHS = {
    "income": "financials/income-statement/",
    "metrics": "financials/metrics/",
    "balance_sheet": "financials/balance-sheet/",
    "cash_flow": "financials/cash-flow-statement/",
    "ratios": "financials/ratios/",
}
# What a scan downloads. `ratios` (stale, 4 rows) and `metrics` (company-specific segment revenue,
# values like "960.49M") are left out; see GOTCHAS. NOTE: the free tier shows only part of each
# table (no liabilities/equity, no capex/FCF) - an open decision, ROADMAP D19.
DEFAULT_STATEMENTS = ("income", "balance_sheet", "cash_flow")

Row = tuple[str, str, float | None]  # (item, period, value)


class ParseError(ValueError):
    """The page has a table but its content is not what we expect."""


@dataclass
class FetchOutcome:
    status: str  # ok | blocked | failed | no_table
    rows: list[Row] = field(default_factory=list)
    latest_period: str | None = None
    detail: str = ""  # short reason / sample for parse_failures (never headers)


def statement_url(symbol: str, statement: str) -> str:
    return f"{BASE}/stocks/{symbol.lower()}/{STATEMENT_PATHS[statement]}"


def parse_number(text: str) -> float | None:
    """'1,316.0' -> 1316.0; '8.77%' -> 8.77; '-', '—', '' -> None. Anything else raises."""
    t = text.strip().replace(",", "").replace("$", "").replace("%", "")
    if t in ("", "-", "—", "–", "n/a", "N/A", "NaN"):
        return None
    try:
        return float(t)
    except ValueError as exc:
        raise ParseError(f"not a number: {text!r}") from exc


def parse_statement_table(html: str) -> tuple[list[Row], str | None]:
    """Return (rows, latest_period) from the financials table; ([], None) if there is none.

    Columns whose header or cells say "Upgrade" (paid-only) are skipped. A row whose cells carry
    '%' gets " (%)" appended to its name unless it already ends with it (same names as v1).
    """
    table = BeautifulSoup(html, "html.parser").select_one("table.financials-table")
    if table is None:
        return [], None
    header_row = table.select_one("thead tr")
    if header_row is None:
        raise ParseError("table has no header row")
    periods = [c.get_text(strip=True) for c in header_row.find_all(["th", "td"])]
    if len(periods) < 2:
        raise ParseError("table header has no period columns")

    skip = {i for i, p in enumerate(periods) if p == "Upgrade"}
    rows: list[Row] = []
    for tr in table.select("tbody tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        if not cells or not cells[0]:
            continue
        if len(cells) != len(periods):
            raise ParseError(f"row {cells[0]!r} has {len(cells)} cells, header {len(periods)}")
        item = cells[0]
        if any("%" in c for c in cells[1:]) and not item.endswith("(%)"):
            item += " (%)"
        for i in range(1, len(cells)):
            if i in skip or cells[i] == "Upgrade":
                continue
            rows.append((item, periods[i], parse_number(cells[i])))
    if not rows:
        raise ParseError("table has no data rows")
    latest = next(
        (p for i, p in enumerate(periods) if i > 0 and i not in skip and p != "TTM"), None
    )
    return rows, latest


def is_challenge(resp: httpx.Response) -> bool:
    return (
        bool(resp.headers.get("cf-mitigated"))
        or "Just a moment" in resp.text[:2000]
        or "Access Denied" in resp.text[:2000]
    )


class StatementFetcher:
    """Downloads one statement page at a time. Pacing between requests is the caller's job
    (see jobs/refresh.py); this class only bounds retries per request."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        retries: int = 2,
        retry_wait: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.client = client or httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
        self.retries = retries
        self.retry_wait = retry_wait
        self._sleep = sleep

    def fetch(self, symbol: str, statement: str) -> FetchOutcome:
        url = statement_url(symbol, statement)
        resp = None
        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                resp = self.client.get(url)
            except httpx.TransportError as exc:
                resp = None
                last_error = type(exc).__name__
            else:
                if resp.status_code < 500 or is_challenge(resp):
                    break
                last_error = f"HTTP {resp.status_code}"
            if attempt < self.retries:
                self._sleep(self.retry_wait * (attempt + 1))
        if resp is None or resp.status_code >= 500:
            return FetchOutcome("failed", detail=last_error)

        if resp.status_code == 429 or is_challenge(resp):
            return FetchOutcome("blocked", detail=f"HTTP {resp.status_code}")
        if resp.status_code == 404:
            return FetchOutcome("failed", detail="HTTP 404")
        if resp.status_code != 200:
            return FetchOutcome("failed", detail=f"HTTP {resp.status_code}")
        try:
            rows, latest = parse_statement_table(resp.text)
        except ParseError as exc:
            return FetchOutcome("failed", detail=f"parse error: {exc}")
        if not rows:
            return FetchOutcome("no_table", detail=resp.text[:300])
        return FetchOutcome("ok", rows, latest)


def jitter(
    low: float = 3.0, high: float = 6.0, rng: Callable[[float, float], float] = random.uniform
) -> float:
    return rng(low, high)
