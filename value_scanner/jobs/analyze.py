"""Turn a run's snapshots and stored statements into classifications, criteria results and
scores in the database (C2-C8 wired together). Only stocks that are in the screen are analysed.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, replace

from value_scanner.analysis.classify import Classification, classify
from value_scanner.analysis.criteria import Result, Status
from value_scanner.analysis.gurus.fisher import evaluate_fisher
from value_scanner.analysis.gurus.graham import evaluate_graham
from value_scanner.analysis.gurus.piotroski import evaluate_piotroski
from value_scanner.analysis.gurus.screen import evaluate_screen
from value_scanner.analysis.scoring import (
    guru_score,
    is_candidate,
    opportunity,
    opportunity_components,
    quality,
)
from value_scanner.analysis.statements import Statements
from value_scanner.storage.repo import Repository

# Tests that make no sense for banks and insurers (docs/classification-doubts.md, doubt 1).
NOT_FOR_FINANCIALS = {
    ("screen", "current_ratio"),
    ("graham", "current_ratio"),
    ("graham", "working_capital"),
    ("fisher", "ps"),
    ("fisher", "rd"),
    ("piotroski", "current_ratio"),
}


@dataclass(frozen=True)
class AnalysisSummary:
    analysed: int
    candidates: list[str]
    unranked: list[str]  # stocks with no quality score (too little data)


def _not_applicable(result: Result) -> Result:
    return replace(
        result, status=Status.NA, strength=None, note="not applicable to financial companies"
    )


def analyse_stock(
    stmts: Statements,
    cls: Classification,
    snap,
    sector_pb_median: float | None,
) -> list[Result]:
    """All criteria for one stock; `snap` is its screener_snapshots row."""
    pe, pb, ps = snap["pe_ratio"], snap["pb_ratio"], snap["ps_ratio"]
    results = [
        *evaluate_screen(stmts, snap["market_cap"], pe),
        *evaluate_graham(stmts, pe, pb, cls.pe_limit),
        *evaluate_fisher(
            stmts, ps, snap["market_cap"], cyclical=cls.cyclical, rd_applies=cls.rd_applies
        ),
        *evaluate_piotroski(stmts, pb, sector_pb_median, cls.pb_applies),
    ]
    if cls.financial:
        results = [
            _not_applicable(r) if (r.guru, r.criterion_id) in NOT_FOR_FINANCIALS else r
            for r in results
        ]
    return results


def analyse_run(repo: Repository, run_id: int) -> AnalysisSummary:
    snaps = repo.snapshots_for_run(run_id)
    companies = {r["symbol"]: r for r in repo.conn.execute("SELECT * FROM companies")}

    pb_by_sector: dict[str, list[float]] = {}
    for symbol, snap in snaps.items():
        sector, pb = companies[symbol]["sector"], snap["pb_ratio"]
        if sector and pb is not None and pb > 0:
            pb_by_sector.setdefault(sector, []).append(pb)

    candidates, unranked, count = [], [], 0
    with repo.transaction():
        for symbol, snap in sorted(snaps.items()):
            if not snap["in_screen"]:
                continue
            company = companies[symbol]
            cls = classify(company["sector"], company["industry"])
            pbs = pb_by_sector.get(company["sector"] or "", [])
            median = statistics.median(pbs) if len(pbs) >= 3 else None
            results = analyse_stock(Statements.from_repo(repo, symbol), cls, snap, median)

            repo.save_classification(run_id, symbol, cls.labels or {"regular": "no special class"})
            repo.save_results(run_id, symbol, [r.as_row() for r in results])
            scores = {}
            for guru in ("screen", "graham", "fisher", "piotroski"):
                scores[guru] = guru_score(r for r in results if r.guru == guru)
                repo.save_score(run_id, symbol, guru, scores[guru].score, scores[guru].coverage)
            q = quality(scores)
            repo.save_score(run_id, symbol, "quality", q, None)
            components = opportunity_components(
                snap["pe_ratio"],
                snap["pb_ratio"],
                snap["ps_ratio"],
                snap["pe_ratio_5y"],
                tech=cls.tech,
                cyclical=cls.cyclical,
            )
            opp = opportunity(components)
            repo.save_score(run_id, symbol, "opportunity", opp, None, components)
            count += 1
            if q is None:
                unranked.append(symbol)
            if is_candidate(q, opp):
                candidates.append(symbol)
    return AnalysisSummary(count, candidates, unranked)
