"""Shape database rows into the dashboard's response models (the web app only reads the DB)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from value_scanner.analysis import rows
from value_scanner.analysis.criteria import Criterion
from value_scanner.analysis.docs import GURUS, OPPORTUNITY_DOCS, OPPORTUNITY_NOTE, SCORING
from value_scanner.analysis.scoring import (
    CANDIDATE_OPPORTUNITY,
    CANDIDATE_QUALITY,
    is_candidate,
)
from value_scanner.analysis.statements import Statements
from value_scanner.api import schemas
from value_scanner.storage.repo import Repository

GURU_KEYS = ("screen", "graham", "fisher", "piotroski")

def _all_criteria() -> dict[tuple[str, str], Criterion]:
    return {(g, c.id): c for g, (_, crit) in GURUS.items() for c in crit.values()}


def _gurus(
    scores: dict[str, Any], counts: dict[str, tuple[int, int, int]]
) -> dict[str, schemas.GuruScoreOut]:
    out = {}
    for guru in GURU_KEYS:
        s = scores.get(guru) or {}
        passed, computed, total = counts.get(guru, (0, 0, 0))
        out[guru] = schemas.GuruScoreOut(
            score=s.get("score"),
            coverage=s.get("coverage"),
            passed=passed,
            computed=computed,
            total=total,
        )
    return out


def run_ref(run: sqlite3.Row) -> schemas.RunRef:
    return schemas.RunRef(
        id=run["id"],
        started_at=run["started_at"],
        finished_at=run["finished_at"],
        summary=run["summary"],
    )


def stocks_view(repo: Repository) -> schemas.StocksOut:
    run = repo.latest_analysed_run()
    base = {"quality_min": CANDIDATE_QUALITY, "opportunity_min": CANDIDATE_OPPORTUNITY}
    if run is None:
        return schemas.StocksOut(run=None, stocks=[], **base)
    counts = repo.result_counts(run["id"])
    out = []
    for row in repo.stock_table(run["id"]):
        q = (row["scores"].get("quality") or {}).get("score")
        o = (row["scores"].get("opportunity") or {}).get("score")
        out.append(
            schemas.StockRowOut(
                symbol=row["symbol"],
                name=row["name"],
                sector=row["sector"],
                industry=row["industry"],
                country=row["country"],
                exchange=row["exchange"],
                labels=row["labels"],
                price=row["price"],
                market_cap=row["market_cap"],
                pe_ratio=row["pe_ratio"],
                ps_ratio=row["ps_ratio"],
                pb_ratio=row["pb_ratio"],
                gurus=_gurus(row["scores"], counts.get(row["symbol"], {})),
                quality=q,
                opportunity=o,
                candidate=is_candidate(q, o),
            )
        )
    return schemas.StocksOut(run=run_ref(run), stocks=out, **base)


def _series(stmts: Statements) -> schemas.SeriesOut:
    years = list(reversed(stmts.years()[:5]))

    def pick(item: str) -> list[float | None]:
        return [stmts.in_year(item, y) for y in years]

    def ratio(num: str, den: str) -> list[float | None]:
        out = []
        for n, d in zip(pick(num), pick(den), strict=True):
            out.append(None if n is None or not d or d <= 0 else round(100 * n / d, 2))
        return out

    return schemas.SeriesOut(
        years=[str(y) for y in years],
        eps=pick(rows.EPS_DILUTED),
        net_margin=ratio(rows.NET_INCOME, rows.REVENUE),
        roe=ratio(rows.NET_INCOME, rows.EQUITY),
    )


def _event(row: sqlite3.Row) -> schemas.EventOut:
    keys = row.keys()
    return schemas.EventOut(
        id=row["id"],
        run_id=row["run_id"],
        symbol=row["symbol"],
        name=row["name"] if "name" in keys else None,
        direction=row["direction"],
        reason_type=row["reason_type"],
        detail=json.loads(row["detail"]) if row["detail"] else None,
        created_at=row["created_at"],
    )


def history_view(repo: Repository) -> schemas.HistoryOut:
    return schemas.HistoryOut(events=[_event(r) for r in repo.membership_history()])


def stock_view(repo: Repository, symbol: str) -> schemas.StockDetailOut | None:
    company = repo.get_company(symbol)
    run = repo.latest_analysed_run()
    if company is None or run is None:
        return None
    results = repo.results_for(run["id"], symbol)
    if not results:
        return None
    defs = _all_criteria()
    order = {key: i for i, key in enumerate(defs)}  # lesson order, as in the criteria docs
    criteria = []
    for r in sorted(results, key=lambda r: order.get((r["guru"], r["criterion_id"]), 999)):
        d = defs.get((r["guru"], r["criterion_id"]))
        criteria.append(
            schemas.CriterionOut(
                guru=r["guru"],
                id=r["criterion_id"],
                title=d.title if d else r["criterion_id"],
                formula=d.formula if d else "",
                note=d.note if d else "",
                direction=d.direction if d else ">",
                comparative=r["guru"] == "piotroski",
                status=r["status"],
                value=r["value"],
                threshold=r["threshold"],
                strength=r["strength"],
                result_note=r["note"],
            )
        )
    scores = {
        r["kind"]: {"score": r["score"], "coverage": r["coverage"]}
        for r in repo.scores_for(run["id"], symbol)
    }
    counts = repo.result_counts(run["id"]).get(symbol, {})
    q = (scores.get("quality") or {}).get("score")
    o = (scores.get("opportunity") or {}).get("score")
    values = {r["component"]: r["value"] for r in repo.score_components_for(run["id"], symbol)}
    components = [
        schemas.ComponentOut(id=cid, title=title, formula=formula, value=values.get(cid))
        for cid, (title, formula) in OPPORTUNITY_DOCS.items()
    ]
    snap = repo.snapshot_for(run["id"], symbol)
    return schemas.StockDetailOut(
        symbol=symbol,
        name=company["name"],
        sector=company["sector"],
        industry=company["industry"],
        country=company["country"],
        exchange=company["exchange"],
        run=run_ref(run),
        labels=[
            schemas.LabelOut(label=r["label"], reason=r["reason"])
            for r in repo.classification_for(run["id"], symbol)
        ],
        quality=q,
        opportunity=o,
        candidate=is_candidate(q, o),
        gurus=_gurus(scores, counts),
        snapshot=(
            schemas.SnapshotOut(
                **{
                    k: snap[k]
                    for k in schemas.SnapshotOut.model_fields  # same column names as the table
                }
            )
            if snap
            else None
        ),
        criteria=criteria,
        components=components,
        series=_series(Statements.from_repo(repo, symbol)),
        history={
            kind: [
                schemas.HistoryPoint(
                    run_id=h["run_id"], started_at=h["started_at"], score=h["score"]
                )
                for h in repo.score_history(symbol, kind)
            ]
            for kind in ("quality", "opportunity")
        },
        events=[_event(e) for e in repo.membership_events(symbol)],
    )


def criteria_view() -> schemas.CriteriaOut:
    return schemas.CriteriaOut(
        gurus=[
            schemas.CriteriaGuru(
                guru=g,
                title=title,
                criteria=[
                    schemas.CriterionDoc(
                        id=c.id,
                        title=c.title,
                        formula=c.formula,
                        direction=c.direction,
                        threshold=c.threshold,
                        note=c.note,
                    )
                    for c in crit.values()
                ],
            )
            for g, (title, crit) in GURUS.items()
        ],
        opportunity=[
            schemas.ComponentOut(id=cid, title=title, formula=formula, value=None)
            for cid, (title, formula) in OPPORTUNITY_DOCS.items()
        ],
        scoring=[SCORING.strip(), OPPORTUNITY_NOTE],
        quality_min=CANDIDATE_QUALITY,
        opportunity_min=CANDIDATE_OPPORTUNITY,
    )
