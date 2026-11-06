"""Persist the screener universe for a run and record who entered or left the screen (B3, E6)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from value_scanner.sources.screener import (
    ALMOST_MAX_FAILED,
    FILTERS,
    MIN_UNIVERSE_RATIO,
    Blocked,
    ScreenerStock,
    StructureChanged,
    Universe,
    dedupe_share_classes,
    evaluate,
    fetch_universe,
)
from value_scanner.storage.repo import Repository

# screener data-point id -> screener_snapshots column
SNAPSHOT_FIELDS = {
    "price": "price",
    "priceDate": "price_date",
    "marketCap": "market_cap",
    "peRatio": "pe_ratio",
    "psRatio": "ps_ratio",
    "pbRatio": "pb_ratio",
    "pOcfRatio": "pocf_ratio",
    "peRatio5Y": "pe_ratio_5y",
    "lastEarningsDate": "last_earnings_date",
    "nextEarningsDate": "next_earnings_date",
    "lastReportDate": "last_report_date",
    "revenueGrowth5Y": "revenue_growth_5y",
    "profitMargin": "profit_margin",
    "epsGrowth5Y": "eps_growth_5y",
    "debtEquity": "debt_equity",
    "currentRatio": "current_ratio",
    "roe5y": "roe_5y",
}
PRICE_DRIVEN = {"marketCap", "peRatio"}  # filters that move with the price alone
UNIVERSE_COUNT_KEY = "universe_count"


@dataclass(frozen=True)
class UniverseResult:
    total: int
    in_screen: list[str]
    almost: list[str]
    dropped_share_classes: list[str]
    entered: list[str]
    exited: list[str]


def _passes(filter_name: str, value: float | None) -> bool:
    if value is None:
        return False
    op, threshold = FILTERS[filter_name]
    return value > threshold if op == ">" else value < threshold


def _classify_change(prev, stock: ScreenerStock, flipped: list[str]) -> tuple[str, dict]:
    """Reason type and detail for a stock whose membership flipped (prev = old snapshot row)."""
    detail = {}
    missing = False
    for name in flipped:
        before = prev[SNAPSHOT_FIELDS[name]]
        after = stock.get(name)
        detail[name] = {"before": before, "after": after}
        missing = missing or before is None or after is None
    if missing:
        return "data", detail
    if prev["last_earnings_date"] != stock.get("lastEarningsDate"):
        return "report", detail
    if set(flipped) <= PRICE_DRIVEN:
        return "price", detail
    return "report", detail


def record_universe(repo: Repository, run_id: int, universe: Universe) -> UniverseResult:
    """Store snapshots for stocks in the screen or almost in it, and the membership changes
    against the previous run. Raises StructureChanged when the universe shrank suspiciously."""
    total = len(universe.stocks)
    previous_total = repo.get_setting(UNIVERSE_COUNT_KEY)
    if previous_total and total < MIN_UNIVERSE_RATIO * int(previous_total):
        raise StructureChanged(f"universe shrank from {previous_total} to {total} stocks")

    outcomes = {s.symbol: evaluate(s) for s in universe.stocks.values()}
    candidates = [
        s for s in universe.stocks.values() if len(outcomes[s.symbol].failed) <= ALMOST_MAX_FAILED
    ]
    kept, dropped = dedupe_share_classes(candidates)

    row = repo.conn.execute(
        "SELECT MAX(run_id) FROM screener_snapshots WHERE run_id < ? "
        "AND run_id IN (SELECT id FROM runs WHERE kind <> 'adhoc')",
        (run_id,),
    ).fetchone()
    previous_run = row[0]
    previous = repo.snapshots_for_run(previous_run) if previous_run else {}
    known_before = {
        r["symbol"] for r in repo.conn.execute("SELECT symbol FROM companies").fetchall()
    }

    in_screen, almost, entered, exited = [], [], [], []
    with repo.transaction():
        for stock in kept:
            outcome = outcomes[stock.symbol]
            repo.upsert_company(
                stock.symbol,
                name=stock.name,
                country=stock.get("country"),
                exchange=stock.get("exchange"),
                sector=stock.get("sector"),
                industry=stock.get("industry"),
            )
            fields = {col: stock.get(key) for key, col in SNAPSHOT_FIELDS.items()}
            repo.save_snapshot(
                run_id,
                stock.symbol,
                {**fields, "in_screen": int(outcome.passed), "filters_failed": len(outcome.failed)},
            )
            (in_screen if outcome.passed else almost).append(stock.symbol)

        if previous_run:
            entered, exited = _membership_changes(
                repo, run_id, universe, kept, in_screen, previous, known_before
            )
        repo.set_setting(UNIVERSE_COUNT_KEY, str(total))

    return UniverseResult(total, in_screen, almost, dropped, entered, exited)


def _company_key(name: str | None, symbol: str) -> str:
    return (name or symbol).strip().casefold()


def _membership_changes(repo, run_id, universe, kept, in_screen, previous, known_before):
    """Compare per company (not per symbol) so a share-class swap (GOOG -> GOOGL, chosen by
    volume) is not reported as one company leaving and another entering."""
    names = {
        r["symbol"]: r["name"]
        for r in repo.conn.execute("SELECT symbol, name FROM companies").fetchall()
    }
    was = {_company_key(names.get(sym), sym): sym for sym, r in previous.items() if r["in_screen"]}
    kept_by_symbol = {s.symbol: s for s in kept}
    now = {_company_key(kept_by_symbol[sym].name, sym): sym for sym in in_screen}
    entered, exited = [], []
    for key in sorted(now.keys() - was.keys()):
        symbol = now[key]
        entered.append(symbol)
        _record_enter(repo, run_id, kept_by_symbol[symbol], previous, known_before)
    for key in sorted(was.keys() - now.keys()):
        symbol = was[key]
        exited.append(symbol)
        _record_exit(repo, run_id, symbol, universe, previous)
    return entered, exited


def _flipped(prev, stock: ScreenerStock) -> list[str]:
    return [n for n in FILTERS if _passes(n, prev[SNAPSHOT_FIELDS[n]]) != _passes(n, stock.get(n))]


def _record_enter(repo, run_id, stock, previous, known_before) -> None:
    symbol = stock.symbol
    prev = previous.get(symbol)
    if prev is None:
        if symbol not in known_before:
            repo.add_membership_event(run_id, symbol, "enter", "new_symbol", None)
        else:  # known earlier but outside the "almost" zone last time: no values to compare
            repo.add_membership_event(
                run_id, symbol, "enter", "data", {"note": "no previous snapshot values"}
            )
        return
    reason, detail = _classify_change(prev, stock, _flipped(prev, stock))
    repo.add_membership_event(run_id, symbol, "enter", reason, detail)


def _record_exit(repo, run_id, symbol, universe, previous) -> None:
    stock = universe.stocks.get(symbol)
    if stock is None:
        repo.add_membership_event(run_id, symbol, "exit", "delisted", None)
        return
    reason, detail = _classify_change(previous[symbol], stock, _flipped(previous[symbol], stock))
    repo.add_membership_event(run_id, symbol, "exit", reason, detail)


def refresh_universe(
    repo: Repository,
    run_id: int,
    fetch: Callable[[], Universe] = fetch_universe,
) -> UniverseResult:
    """Fetch and record the universe. Blocked or changed-structure errors are logged, stored as
    an alert row (email delivery is B4) and re-raised so the run can stop cleanly."""
    try:
        universe = fetch()
        return record_universe(repo, run_id, universe)
    except Blocked as exc:
        repo.log(run_id, "error", f"screener blocked: {exc}")
        repo.add_alert("blocked", "StockAnalysis blocked the screener request", str(exc), run_id)
        raise
    except StructureChanged as exc:
        repo.log(run_id, "error", f"screener structure changed: {exc}")
        repo.add_alert(
            "structure_changed", "Screener JSON changed shape", json.dumps(str(exc)), run_id
        )
        raise
