-- Initial schema (plans/v2-rebuild.md section 2). Portable SQL: no SQLite-only syntax except
-- INTEGER PRIMARY KEY ids (Postgres: GENERATED ... AS IDENTITY). Timestamps are ISO-8601 UTC
-- strings ("2026-11-05T12:00:00Z"), which sort correctly as text. Booleans are 0/1.

-- ── settings and operations ─────────────────────────────────────────────────────────────────
CREATE TABLE settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE runs (
    id             INTEGER PRIMARY KEY,
    kind           TEXT NOT NULL CHECK (kind IN ('scheduled', 'manual', 'cli')),
    status         TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed', 'interrupted', 'blocked')),
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    progress_done  INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    summary        TEXT,
    error          TEXT
);
-- The run lock: at most one row may be 'running' (E5).
CREATE UNIQUE INDEX runs_one_running ON runs (status) WHERE status = 'running';
CREATE INDEX runs_started_at ON runs (started_at);

CREATE TABLE run_log (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    ts      TEXT NOT NULL,
    level   TEXT NOT NULL CHECK (level IN ('debug', 'info', 'warning', 'error')),
    message TEXT NOT NULL
);
CREATE INDEX run_log_run ON run_log (run_id, id);
CREATE INDEX run_log_ts ON run_log (ts);

CREATE TABLE alerts (
    id         INTEGER PRIMARY KEY,
    run_id     INTEGER REFERENCES runs (id) ON DELETE SET NULL,
    kind       TEXT NOT NULL,  -- blocked | structure_changed | suspicious_data | extraction_failed | billing | ...
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    sent_at    TEXT,
    error      TEXT
);
CREATE INDEX alerts_created_at ON alerts (created_at);

-- A short sample of every parse failure (never headers), so we know what to fix.
CREATE TABLE parse_failures (
    id         INTEGER PRIMARY KEY,
    run_id     INTEGER REFERENCES runs (id) ON DELETE SET NULL,
    symbol     TEXT,
    source     TEXT NOT NULL,
    kind       TEXT NOT NULL,
    sample     TEXT,
    created_at TEXT NOT NULL
);

-- ── companies ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE companies (
    symbol          TEXT PRIMARY KEY,
    name            TEXT,
    country         TEXT,
    exchange        TEXT,
    sector          TEXT,  -- from the screener JSON; drives our classification
    industry        TEXT,
    sic_description TEXT,  -- from the SEC, secondary
    cik             TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);

-- ── screener snapshots: one row per run and symbol that is in the screen or "almost" ───────
CREATE TABLE screener_snapshots (
    id                 INTEGER PRIMARY KEY,
    run_id             INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol             TEXT NOT NULL REFERENCES companies (symbol),
    captured_at        TEXT NOT NULL,
    in_screen          INTEGER NOT NULL CHECK (in_screen IN (0, 1)),
    filters_failed     INTEGER NOT NULL DEFAULT 0,
    price              REAL,
    price_date         TEXT,
    market_cap         REAL,
    pe_ratio           REAL,
    ps_ratio           REAL,
    pb_ratio           REAL,
    pocf_ratio         REAL,
    pe_ratio_5y        REAL,
    last_earnings_date TEXT,
    next_earnings_date TEXT,
    -- the 8 initial-screen fields (lesson 3)
    revenue_growth_5y  REAL,
    profit_margin      REAL,
    eps_growth_5y      REAL,
    debt_equity        REAL,
    current_ratio      REAL,
    roe_5y             REAL,
    UNIQUE (run_id, symbol)
);
CREATE INDEX screener_snapshots_symbol ON screener_snapshots (symbol, captured_at);
CREATE INDEX screener_snapshots_captured ON screener_snapshots (captured_at);

-- ── financial statements (long format) ─────────────────────────────────────────────────────
-- statement: income | balance_sheet | cash_flow | metrics | ratios
CREATE TABLE statement_fetches (
    id            INTEGER PRIMARY KEY,
    run_id        INTEGER REFERENCES runs (id) ON DELETE SET NULL,
    symbol        TEXT NOT NULL REFERENCES companies (symbol),
    statement     TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    source        TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('ok', 'blocked', 'failed', 'no_table')),
    latest_period TEXT  -- most recent reported period in the table, e.g. "FY 2025"
);
CREATE INDEX statement_fetches_lookup ON statement_fetches (symbol, statement, fetched_at);

CREATE TABLE statement_values (
    fetch_id INTEGER NOT NULL REFERENCES statement_fetches (id) ON DELETE CASCADE,
    item     TEXT NOT NULL,
    period   TEXT NOT NULL,  -- "TTM", "FY 2024", "Q3 2025", ...
    value    REAL,           -- NULL = the site showed no value
    PRIMARY KEY (fetch_id, item, period)
);

-- ── classification, criteria results and scores (every run is kept) ────────────────────────
CREATE TABLE classifications (
    run_id INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol TEXT NOT NULL REFERENCES companies (symbol),
    label  TEXT NOT NULL,  -- tech | pharma | cyclical | growth | financial | ...
    reason TEXT,
    PRIMARY KEY (run_id, symbol, label)
);

CREATE TABLE results (
    run_id       INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL REFERENCES companies (symbol),
    guru         TEXT NOT NULL CHECK (guru IN ('screen', 'graham', 'fisher', 'piotroski')),
    criterion_id TEXT NOT NULL,
    value        REAL,
    threshold    REAL,
    status       TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'NA')),
    strength     REAL CHECK (strength IS NULL OR (strength >= 0 AND strength <= 1)),
    note         TEXT,
    PRIMARY KEY (run_id, symbol, guru, criterion_id)
);

CREATE TABLE scores (
    run_id   INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol   TEXT NOT NULL REFERENCES companies (symbol),
    kind     TEXT NOT NULL CHECK (kind IN
                 ('screen', 'graham', 'fisher', 'piotroski', 'quality', 'opportunity')),
    score    REAL,           -- NULL = not ranked (coverage too low)
    coverage REAL,
    PRIMARY KEY (run_id, symbol, kind)
);

CREATE TABLE score_components (
    run_id     INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol     TEXT NOT NULL REFERENCES companies (symbol),
    kind       TEXT NOT NULL,  -- the score this component belongs to, e.g. 'opportunity'
    component  TEXT NOT NULL,  -- e.g. graham_number | fair_pe | vs_history | price_to_sales
    value      REAL,           -- NULL = does not apply to this stock
    PRIMARY KEY (run_id, symbol, kind, component)
);

-- ── screen membership history (E6) ─────────────────────────────────────────────────────────
CREATE TABLE membership_events (
    id          INTEGER PRIMARY KEY,
    run_id      INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol      TEXT NOT NULL REFERENCES companies (symbol),
    direction   TEXT NOT NULL CHECK (direction IN ('enter', 'exit')),
    reason_type TEXT NOT NULL CHECK (reason_type IN
                    ('price', 'report', 'new_symbol', 'delisted', 'data')),
    detail      TEXT,  -- JSON: which filter flipped, value before and after
    created_at  TEXT NOT NULL
);
CREATE INDEX membership_events_symbol ON membership_events (symbol, created_at);
CREATE INDEX membership_events_created ON membership_events (created_at);

-- ── business profiles (E7) ─────────────────────────────────────────────────────────────────
CREATE TABLE profiles (
    id             INTEGER PRIMARY KEY,
    symbol         TEXT NOT NULL REFERENCES companies (symbol),
    text           TEXT NOT NULL,
    accession      TEXT NOT NULL,  -- SEC accession number of the filing summarised
    filing_date    TEXT,
    source_url     TEXT,
    model          TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    UNIQUE (symbol, accession, prompt_version)
);
