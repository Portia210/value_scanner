# ARCHITECTURE

**Derived from source on 2026-11-06 (branch `v2`).** Source code outranks this file; if they
disagree, report it and re-derive the section. Target design and history: [plans/v2-rebuild.md](plans/v2-rebuild.md);
v1 defects: [plans/v2-audit.md](plans/v2-audit.md).

## Overview
`value_scanner/` (v2) scans StockAnalysis.com anonymously with httpx (no browser, no login),
stores everything in one SQLite file (`DB_PATH`), evaluates the lessons' criteria per stock and
serves a React dashboard from FastAPI. A scheduler inside the same process starts a scan every N
days; "Run now" starts one on demand. The v1 code (`main.py`, `pipeline/`, `reports_checks/`,
`company_classifiers/`, `playwright_utils/`, `utils/`, `enums/`, `constants/`) is still in the repo
only until C9 (old-vs-new comparison) is closed; v2 does not import it.

## Run flow (`jobs/pipeline.py: run_scan`)
1. Take the run lock (unique partial index: one `running` row) and log.
2. `sources/screener.py` — two requests to StockAnalysis' screener JSON (`screener/initial`,
   `data-points`); the 8 lesson-3 filters are applied **in code** (`FILTERS`), share classes are
   de-duplicated, structure changes raise `StructureChanged`, a Cloudflare challenge raises `Blocked`.
3. `jobs/universe.py` — snapshots of every stock in the screen or "almost" (≤2 failed filters) →
   `screener_snapshots`; entries/exits vs the previous run → `membership_events` (reason: price /
   report / new_symbol / delisted / data).
4. `jobs/refresh.py` + `sources/stockanalysis.py` — download income / balance-sheet / cash-flow
   pages only when the screener's `lastReportDate` is newer than the one stored with our last download (R5; D18 earnings-date rules when either date is unknown; 120-day backstop), 4 parallel workers with 0.5–1 s between a worker's requests (R6; DB written from one thread only)
   dozen requests; results in long format (`statement_values`).
5. `jobs/analyze.py: analyse_run` — classify (`analysis/classify.py`), evaluate the criteria
   (`analysis/gurus/{screen,graham,fisher,piotroski}.py`), score (`analysis/scoring.py`) → `results`,
   `scores`, `score_components`, `classifications`.
6. `jobs/alerts.py` — alerts are stored in `alerts` and emailed to `MY_EMAIL` (SMTP_*); a delivery
   failure never fails a run.

## Web (`api/`, `frontend/`)
- `api/app.py` `create_app`: JSON API (`/api/stocks`, `/api/stocks/{symbol}`, `/api/criteria`,
  `/api/history`, `/api/runs`, `/api/runs/{id}/log`, `/api/settings`, `/api/auth/*`), response models in
  `api/schemas.py`, row→model shaping in `api/views.py`. One SQLite connection per request.
  Serves `frontend/dist` (SPA fallback) when it exists.
- Auth: `DASHBOARD_PASSWORD` + `SESSION_SECRET` → signed cookie + CSRF header; without a password
  it is **local mode** (localhost Host only, `serve` refuses a non-loopback bind).
- `frontend/`: Vite + React + TypeScript + Mantine (RTL, light/dark) + ECharts + TanStack Query.
  Types come from the API: `python -m value_scanner openapi > frontend/src/api/openapi.json &&
  pnpm -C frontend gen:api` (a test fails when the committed schema is stale).
- `jobs/scheduler.py`: APScheduler checks every 15 min whether `days_between_runs` passed since the
  last successful run; `serve` starts it and marks runs left `running` as `interrupted`.

## Data (SQLite, `storage/migrations/0001_initial.sql`)
settings, runs, run_log, alerts, parse_failures · companies · screener_snapshots ·
statement_fetches/statement_values · classifications, results, scores, score_components ·
membership_events · profiles (E7: created only on demand, never by a scan). `storage/repo.py` is the only module that talks to
the DB. Retention: run_log 90 d, snapshots 400 d, 4 latest good statement fetches per stock/statement.
No CSV/JSON/cookie files; `var/` (git-ignored) holds the local DB and legacy v1 snapshots.

## Criteria docs
`docs/criteria/*.md` are generated from the criterion definitions (`python -m value_scanner docs`);
`tests/test_docs.py` fails on drift. The dashboard's "How it is calculated" page reads the same
definitions through `/api/criteria`.

## CLI (`python -m value_scanner <cmd>`)
`run [--limit N]`, `serve [--host --port]`, `docs`, `openapi`, `config`, `test-alert`.

## External services
| Service | Used for | Env var names |
|---|---|---|
| StockAnalysis.com | screener JSON + statement pages (anonymous) | — |
| SMTP (Gmail) | alert emails | `MY_EMAIL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (`GOOGLE_APP_PASSWORD` shortcut) |
| Gemini | company profiles (E7): only the "create description" button or `python -m value_scanner profiles` | `GOOGLE_API_KEY` |
| SEC | contact address in User-Agent (E7) | `MY_EMAIL` |

## Environments & deploy
| Env | Branch | Storage | Notes |
|---|---|---|---|
| local (WSL) | `v2` | `var/value_scanner.db` | `serve` + `run` |
| Railway | — | volume at `/data` | **not deployed yet** (F2); `Dockerfile` written, never built (no Docker in WSL) |

## Verification
`uv run ruff check . && uv run pytest -q` and `pnpm -C frontend build`.
