"""Turn a run's snapshots and stored statements into classifications, criteria results and
scores in the database (C2-C8 wired together). Only stocks that are in the screen are analysed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from value_scanner.analysis.classify import Classification, classify
from value_scanner.analysis.criteria import Result, Status
from value_scanner.analysis.gurus.buffett import evaluate_buffett
from value_scanner.analysis.gurus.fisher import evaluate_fisher
from value_scanner.analysis.gurus.graham import evaluate_graham
from value_scanner.analysis.gurus.neff import evaluate_neff
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
    ("buffett", "earnings_vs_liabilities"),  # a bank's liabilities are its deposits
}
GURUS = ("screen", "graham", "fisher", "piotroski", "buffett", "neff")


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
) -> list[Result]:
    """All criteria for one stock; `snap` is its screener_snapshots row."""
    pe, pb, ps = snap["pe_ratio"], snap["pb_ratio"], snap["ps_ratio"]
    results = [
        *evaluate_screen(
            stmts,
            snap["market_cap"],
            pe,
            revenue_growth_5y=snap["revenue_growth_5y"],
            eps_growth_5y=snap["eps_growth_5y"],
            roe_5y=snap["roe_5y"],
        ),
        *evaluate_graham(stmts, pe, pb, cls.pe_limit),
        *evaluate_fisher(
            stmts,
            ps,
            snap["market_cap"],
            cyclical=cls.cyclical,
            rd_applies=cls.rd_applies,
            net_margin_limit=cls.net_margin_limit,
        ),
        *evaluate_piotroski(stmts),
        *evaluate_buffett(stmts, roe_5y=snap["roe_5y"]),
        *evaluate_neff(
            stmts,
            pe=pe,
            industry_pe=snap["industry_pe"],
            price=snap["price"],
            low_52=snap["low_52"],
            high_52=snap["high_52"],
            eps_growth_5y=snap["eps_growth_5y"],
            revenue_growth_5y=snap["revenue_growth_5y"],
            dividend_yield=snap["dividend_yield"],
            industry_return_median=snap["industry_return_median"],
        ),
    ]
    if cls.financial:
        results = [
            _not_applicable(r) if (r.guru, r.criterion_id) in NOT_FOR_FINANCIALS else r
            for r in results
        ]
    return results


def analyse_and_store(
    repo: Repository, run_id: int, symbol: str, company, snap
) -> tuple[float | None, float | None]:
    """Classify, evaluate and score one stock and store everything for the run.
    Returns (quality, opportunity). The caller owns the transaction."""
    cls = classify(company["sector"], company["industry"])
    results = analyse_stock(Statements.from_repo(repo, symbol), cls, snap)

    repo.save_classification(run_id, symbol, cls.labels or {"regular": "no special class"})
    repo.save_results(run_id, symbol, [r.as_row() for r in results])
    scores = {}
    for guru in GURUS:
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
    return q, opp


def analyse_run(repo: Repository, run_id: int) -> AnalysisSummary:
    snaps = repo.snapshots_for_run(run_id)
    companies = {r["symbol"]: r for r in repo.conn.execute("SELECT * FROM companies")}

    candidates, unranked, count = [], [], 0
    with repo.transaction():
        for symbol, snap in sorted(snaps.items()):
            if not snap["in_screen"]:
                continue
            q, opp = analyse_and_store(repo, run_id, symbol, companies[symbol], snap)
            count += 1
            if q is None:
                unranked.append(symbol)
            if is_candidate(q, opp):
                candidates.append(symbol)
    return AnalysisSummary(count, candidates, unranked)
