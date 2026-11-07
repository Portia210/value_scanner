"""Scores (C7, C8): per-guru score and coverage, overall quality, and buy opportunity.

Defaults of plans/v2-rebuild.md section 3 (decisions D8, D9). NA results are left out of every
average and reported as lower coverage; a guru with too little coverage is not ranked at all.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from value_scanner.analysis.criteria import Result, Status, is_missing

MIN_COVERAGE = 0.6
MIN_GURUS_FOR_QUALITY = 2
CANDIDATE_QUALITY = 0.7
CANDIDATE_OPPORTUNITY = 0.2
FAIR_PE_DEFAULT = 15.0
FAIR_PE_TECH = 25.0
GRAHAM_PRODUCT = 22.5  # 15 x 1.5, the value behind Graham's number


@dataclass(frozen=True)
class GuruScore:
    score: float | None  # None = not ranked (coverage too low or nothing computable)
    coverage: float  # share of the criteria that could be computed
    passed: int
    total: int


def guru_score(results: Iterable[Result]) -> GuruScore:
    results = [r for r in results if r.status != Status.MANUAL]  # a human check is not a test
    scored = [r for r in results if r.status != Status.NA and r.strength is not None]
    total = len(results)
    coverage = len(scored) / total if total else 0.0
    passed = sum(1 for r in results if r.status == Status.PASS)
    if not scored or coverage < MIN_COVERAGE:
        return GuruScore(None, coverage, passed, total)
    return GuruScore(sum(r.strength for r in scored) / len(scored), coverage, passed, total)


def quality(scores: Mapping[str, GuruScore]) -> float | None:
    """Equal-weight mean of the ranked gurus; needs at least two of them."""
    ranked = [s.score for s in scores.values() if s.score is not None]
    return sum(ranked) / len(ranked) if len(ranked) >= MIN_GURUS_FOR_QUALITY else None


def opportunity_components(
    pe: float | None,
    pb: float | None,
    ps: float | None,
    pe_5y: float | None,
    *,
    tech: bool,
    cyclical: bool,
) -> dict[str, float | None]:
    """Margin of safety per method at today's price; None = the method does not apply.

    graham_number: 1 - sqrt(P/E x P/B / 22.5)  (not technology; P/E and P/B positive)
    fair_pe:       1 - P/E / fair P/E          (15, technology 25; P/E positive)
    vs_history:    1 - P/E / 5-year P/E        (the screener's 5-year AVERAGE P/E, not a median)
    price_sales:   1 - P/S / limit             (0.8 cyclical, 1.5 other; not technology)
    """

    def positive(x: float | None) -> bool:
        return not is_missing(x) and x > 0

    out: dict[str, float | None] = dict.fromkeys(
        ("graham_number", "fair_pe", "vs_history", "price_sales")
    )
    if not tech and positive(pe) and positive(pb):
        out["graham_number"] = 1 - math.sqrt(pe * pb / GRAHAM_PRODUCT)
    if positive(pe):
        out["fair_pe"] = 1 - pe / (FAIR_PE_TECH if tech else FAIR_PE_DEFAULT)
    if positive(pe) and positive(pe_5y):
        out["vs_history"] = 1 - pe / pe_5y
    if not tech and positive(ps):
        out["price_sales"] = 1 - ps / (0.8 if cyclical else 1.5)
    return out


def opportunity(components: Mapping[str, float | None]) -> float | None:
    """Median of the applicable components (None if none apply)."""
    values = [v for v in components.values() if v is not None]
    return statistics.median(values) if values else None


def is_candidate(quality_score: float | None, opportunity_score: float | None) -> bool:
    return (
        quality_score is not None
        and opportunity_score is not None
        and quality_score >= CANDIDATE_QUALITY
        and opportunity_score >= CANDIDATE_OPPORTUNITY
    )
