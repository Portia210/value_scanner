"""Response models of the dashboard API. FastAPI turns them into the OpenAPI schema from which
the frontend's TypeScript types are generated (`pnpm -C frontend gen:api`), so the two cannot
drift apart silently."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRef(BaseModel):
    id: int
    started_at: str
    finished_at: str | None = None
    summary: str | None = None


class GuruScoreOut(BaseModel):
    score: float | None  # 0..1; None = not ranked (too little data)
    coverage: float | None
    passed: int
    computed: int  # criteria that could be computed (not NA)
    total: int


class StockRowOut(BaseModel):
    symbol: str
    name: str | None
    sector: str | None
    industry: str | None
    country: str | None
    exchange: str | None
    labels: list[str]
    price: float | None
    market_cap: float | None  # dollars
    pe_ratio: float | None
    ps_ratio: float | None
    pb_ratio: float | None
    gurus: dict[str, GuruScoreOut]
    quality: float | None
    opportunity: float | None
    candidate: bool


class StocksOut(BaseModel):
    run: RunRef | None
    stocks: list[StockRowOut]
    quality_min: float
    opportunity_min: float


class CriterionOut(BaseModel):
    guru: str
    id: str
    title: str
    formula: str
    note: str
    direction: str  # > >= < <=
    comparative: bool  # value is this year's figure and threshold last year's (Piotroski)
    status: str  # PASS | FAIL | NA
    value: float | None
    threshold: float | None
    strength: float | None
    result_note: str | None


class ComponentOut(BaseModel):
    id: str
    title: str
    formula: str
    value: float | None  # None = does not apply to this stock


class SeriesOut(BaseModel):
    years: list[str]  # oldest first
    eps: list[float | None]
    net_margin: list[float | None]  # percent
    roe: list[float | None]  # percent: Net Income / Shareholders' Equity


class SnapshotOut(BaseModel):
    price: float | None
    price_date: str | None
    market_cap: float | None
    pe_ratio: float | None
    ps_ratio: float | None
    pb_ratio: float | None
    pe_ratio_5y: float | None
    last_earnings_date: str | None
    next_earnings_date: str | None


class LabelOut(BaseModel):
    label: str
    reason: str | None


class EventOut(BaseModel):
    id: int
    run_id: int
    symbol: str
    name: str | None = None
    direction: str  # enter | exit
    reason_type: str  # price | report | new_symbol | delisted | data
    detail: dict[str, Any] | None
    created_at: str


class HistoryPoint(BaseModel):
    run_id: int
    started_at: str
    score: float | None


class ProfileOut(BaseModel):
    text: str  # Markdown, Hebrew
    filing_date: str | None
    source_url: str | None
    model: str
    created_at: str


class StockDetailOut(BaseModel):
    symbol: str
    name: str | None
    sector: str | None
    industry: str | None
    country: str | None
    exchange: str | None
    run: RunRef
    labels: list[LabelOut]
    quality: float | None
    opportunity: float | None
    candidate: bool
    gurus: dict[str, GuruScoreOut]
    snapshot: SnapshotOut | None
    criteria: list[CriterionOut]
    components: list[ComponentOut]
    series: SeriesOut
    history: dict[str, list[HistoryPoint]]
    events: list[EventOut]
    profile: ProfileOut | None
    sic_description: str | None


class CriteriaGuru(BaseModel):
    guru: str
    title: str
    criteria: list[CriterionDoc]


class CriterionDoc(BaseModel):
    id: str
    title: str
    formula: str
    direction: str
    threshold: float
    note: str


class CriteriaOut(BaseModel):
    gurus: list[CriteriaGuru]
    opportunity: list[ComponentOut]
    scoring: list[str]
    quality_min: float
    opportunity_min: float


class RunOut(BaseModel):
    id: int
    kind: str
    status: str
    started_at: str
    finished_at: str | None
    progress_done: int
    progress_total: int
    summary: str | None
    error: str | None


class LogLine(BaseModel):
    id: int
    ts: str
    level: str
    message: str


class SettingsOut(BaseModel):
    days_between_runs: int = Field(ge=1, le=60)
    last_run_at: str | None = None  # last successful run
    next_run_at: str | None = None


class HistoryOut(BaseModel):
    events: list[EventOut]


CriteriaGuru.model_rebuild()
