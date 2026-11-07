# CLAUDE.md

> Loaded into every session — keep it short. Facts here were derived from source on
> 2026-11-05; source outranks this file. The previous version described a Playwright
> utilities library and was wrong (audit T1).

## Project facts

**What this is:** A value-investing stock scanner. It scrapes financial statements from
StockAnalysis.com, checks each stock against the guru criteria from the developer's course
(lessons 3–8: initial screen, Graham, Ken Fisher, Piotroski, Buffett, Neff), and scores quality and buy
opportunity. **Being rebuilt as v2:** an online dashboard on Railway with scheduled runs —
see `.claude/plans/v2-rebuild.md`.
**Stack:** Python ≥3.11, uv, pandas, httpx, BeautifulSoup (Playwright only in legacy v1 code). v2 adds a FastAPI
JSON API, APScheduler, SQLite (WAL), and a React + TypeScript + Mantine + ECharts frontend
(Vite, pnpm, Node 20) in `frontend/`, built and served by FastAPI. API types for the frontend
are generated from FastAPI's OpenAPI. Layout/colour reference: `design/dashboard-preview.html`.
**Environment:** WSL Ubuntu locally; target Railway (Docker on python slim, no browser; one volume holding the SQLite file at `DB_PATH`). All data lives in the database — no data folder, no CSV/JSON/cookie files. `MY_EMAIL` (env) is both the alert recipient and the SEC contact address.
**Course material (source of the criteria):** `/mnt/c/Users/hp/Documents/השקעות ערך/שיעור-*.md`.
The lessons flag conflicts between the PDF and the developer's summary — never pick one
silently; they are decisions in ROADMAP.

| Task | Command |
|---|---|
| Install | `uv sync` then `uv run playwright install chromium` |
| Run (current, interactive) | `uv run python main.py` |
| Tests | `uv run pytest -q` |
| Lint | `uv run ruff check .` (`--fix` for imports/format) |
| Secret scan hook | `git config core.hooksPath .githooks` (once per clone) |

**Build gate:** `uv run ruff check . && uv run pytest -q` + `pnpm -C frontend build`.
The pre-commit hook (`.githooks/pre-commit`) runs detect-secrets against `.secrets.baseline` and
refuses `.env`/cookie files. GitHub secret scanning + push protection are enabled on the repo.

**Branches:** `master` — stable. `v2` — rebuild work; push freely; merge to master when v2 is deployed.
Remote `origin` is a **public** GitHub repo.
**Language:** code, comments, commit messages in English. Project docs under `.claude/` in
Hebrew (CLAUDE.md and ARCHITECTURE.md in English). Dashboard UI in Hebrew RTL (pending D10).
Reply to the developer in the language they write in.

## Developer authorization (2026-11-05)

The developer granted full permission to edit, move, rename or delete any file in this
repo and to abandon the current structure, and to run the whole v2 plan without asking
for approval (decisions take the defaults in ROADMAP). Still stop for what needs the
developer: a CAPTCHA, StockAnalysis blocking the server, or secrets they haven't provided.

**Chrome extension (Claude in Chrome):** full permission to use it in the developer's
browser — e.g. to inspect StockAnalysis pages, verify the screener filters, and click
through the deployed dashboard. Don't change account settings or saved screens there.

**Browsers: always headless.** Any Chromium/Playwright I start (scripts, probes, the Playwright MCP) must
run headless (`headless=True`, MCP arg `--headless`) — never open a visible window on the developer's
machine. The Playwright plugin as installed (`npx @playwright/mcp@latest`, no flag) starts headed;
check/adjust before using it. Claude in Chrome is the developer's own browser and is exempt.

**Classification doubts** go to `docs/classification-doubts.md` (Hebrew, written for the
developer): current behavior, what the lessons say, the default in effect, the question.

## UI conventions (from the developer)

- **Show freshness, not run numbers.** Run ids mean nothing to the developer; say *when* the data is
  current: "עדכני להיום (16:40)" / "לאתמול" / "ל-05.11.2026" (`updated()`, `asOf()` in
  `frontend/src/format.ts`). Run ids stay only on the runs screen. Dates of prices/earnings: today /
  yesterday / tomorrow, else the date.
- **Keep it simple for the user (2026-11-06).** Few lines, plain words, one meaning per label; no
  technical terms (period end, TTM, run ids). Around reports/dates show only what the user must act on
  (e.g. "a new report is waiting"). When a screen feels crowded or confusing: cut, don't explain.
- Closable banners where they are informational; explain what a chart shows (axes, units, legend).
- After any backend/API change: bump `API_VERSION` + `frontend/src/api/version.ts` and tell the
  developer to restart `serve` (a stale server breaks the page; the UI warns about it).

## Session start

- Read `.claude/NEXTSESSION.md` and run `git status`.
- Unexpected uncommitted changes are a finding to report, not something to tidy.
- Wait for the developer to name the task. `.claude/ROADMAP.md` is not a self-serve queue.

## Hard rules

- **Assume code and docs may be wrong.** Verify each premise against source and data
  before acting on it; report contradictions instead of working around them.
- **Never expose secrets** — don't read, print or commit `.env`, `cookies.txt`, tokens.
  Env var *names* only. The repo is public.
- **Destructive actions need confirmation** unless covered by the authorization above.
- **Never bypass or game checks/tests.** If a test looks wrong, say so.
- **No new dependency without approval** (list in plan §5, decision D12).
- **"Done" means verified** — run it; for UI, click through it.
- **Missing data is `NA`, never `PASS`.**
- **Never decide a formula or a fallback that the course summaries do not state.** If something is
  missing or unclear, show the developer the problem *before* implementing a substitute. Every
  interpretation already made is listed in `docs/formula-decisions.md` for approval.
- **Always report a failure or anomaly up front** (broken test, hang, wrong earlier claim,
  contradicting data), before continuing. A missing `Long-Term Debt` row means no long-term debt (0).

## Workflow

| Size | Process |
|---|---|
| Trivial | Do → gate → commit |
| Standard | Explore → Plan → wait for Y/N → Code → Verify → commit |
| Large | As Standard + plan file in `.claude/plans/`, ticked as you go |

- Every criterion change gets boundary tests (at, above, below threshold; missing; negative).
- One ROADMAP task per commit. Update docs in the same commit.

## Project memory

| File | Purpose |
|---|---|
| `.claude/NEXTSESSION.md` | Hand-off from the last session |
| `.claude/ROADMAP.md` | Tasks + open decisions (D0–D15) |
| `.claude/ARCHITECTURE.md` | Current structure, derived from source |
| `.claude/GOTCHAS.md` | Known traps |
| `.claude/plans/v2-rebuild.md` | Target design and phases |
| `.claude/plans/v2-audit.md` | Verified defects in the current code (IDs like P1, R3) |

Write less: facts the next session needs, not stories. Replace stale text, don't append.

## Communicating

- Lead with the result. One clear question at a time, with a recommendation.
- If a request looks like a mistake, say why first — then follow the developer's decision.
