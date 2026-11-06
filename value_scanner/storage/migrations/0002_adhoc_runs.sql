-- foreign_keys: off
-- E8: a run kind 'adhoc' (analysis of one ticker on request). SQLite cannot change a CHECK
-- constraint, so the table is rebuilt (the documented 12-step procedure; the migration runner
-- switches foreign keys off around it and verifies them afterwards).
CREATE TABLE runs_new (
    id             INTEGER PRIMARY KEY,
    kind           TEXT NOT NULL CHECK (kind IN ('scheduled', 'manual', 'cli', 'adhoc')),
    status         TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed', 'interrupted', 'blocked')),
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    progress_done  INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    summary        TEXT,
    error          TEXT
);
INSERT INTO runs_new (id, kind, status, started_at, finished_at, progress_done, progress_total, summary, error)
    SELECT id, kind, status, started_at, finished_at, progress_done, progress_total, summary, error FROM runs;
DROP TABLE runs;
ALTER TABLE runs_new RENAME TO runs;
CREATE UNIQUE INDEX runs_one_running ON runs (status) WHERE status = 'running';
CREATE INDEX runs_started_at ON runs (started_at)
