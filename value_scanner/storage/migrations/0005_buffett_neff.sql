-- foreign_keys: off
-- Lessons 7 and 8 (Buffett, Neff): two new gurus, a "MANUAL" result status (a human check), and the
-- screener fields Neff needs. SQLite cannot change a CHECK constraint, so `results` and `scores` are
-- rebuilt. Both are leaf tables (nothing references them), so nothing can cascade - unlike `runs` in
-- migration 0002. The runner switches foreign keys off around it and verifies them afterwards.
ALTER TABLE screener_snapshots ADD COLUMN industry_pe REAL;
ALTER TABLE screener_snapshots ADD COLUMN low_52 REAL;
ALTER TABLE screener_snapshots ADD COLUMN high_52 REAL;
ALTER TABLE screener_snapshots ADD COLUMN dividend_yield REAL;
ALTER TABLE screener_snapshots ADD COLUMN industry_return_median REAL;

CREATE TABLE results_new (
    run_id       INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL REFERENCES companies (symbol),
    guru         TEXT NOT NULL CHECK (guru IN
                     ('screen', 'graham', 'fisher', 'piotroski', 'buffett', 'neff')),
    criterion_id TEXT NOT NULL,
    value        REAL,
    threshold    REAL,
    status       TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'NA', 'MANUAL')),
    strength     REAL CHECK (strength IS NULL OR (strength >= 0 AND strength <= 1)),
    note         TEXT,
    PRIMARY KEY (run_id, symbol, guru, criterion_id)
);
INSERT INTO results_new (run_id, symbol, guru, criterion_id, value, threshold, status, strength, note)
    SELECT run_id, symbol, guru, criterion_id, value, threshold, status, strength, note FROM results;
DROP TABLE results;
ALTER TABLE results_new RENAME TO results;

CREATE TABLE scores_new (
    run_id   INTEGER NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    symbol   TEXT NOT NULL REFERENCES companies (symbol),
    kind     TEXT NOT NULL CHECK (kind IN
                 ('screen', 'graham', 'fisher', 'piotroski', 'buffett', 'neff',
                  'quality', 'opportunity')),
    score    REAL,
    coverage REAL,
    PRIMARY KEY (run_id, symbol, kind)
);
INSERT INTO scores_new (run_id, symbol, kind, score, coverage)
    SELECT run_id, symbol, kind, score, coverage FROM scores;
DROP TABLE scores;
ALTER TABLE scores_new RENAME TO scores
