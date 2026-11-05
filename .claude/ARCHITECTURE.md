# ARCHITECTURE

**Derived from source on 2026-11-05 at `a448e20`** (plus uncommitted changes in
`reports_checks/ken_fisher_check.py`). Source code outranks this file; if they disagree,
report it and re-derive the section. Facts only — the target design lives in
[plans/v2-rebuild.md](plans/v2-rebuild.md), known defects in [plans/v2-audit.md](plans/v2-audit.md).

## Overview
A local, interactive CLI (`main.py`). It logs in to StockAnalysis.com with Playwright, reads a
stock list from the site's screener, downloads four financial statements per stock with
httpx, classifies each company, runs three pass/fail checks, and writes Markdown/CSV reports.
No server, no database, no scheduler.

## Run flow (`main.py`)
1. `ensure_valid_cookies` — validate `cookies.txt`, else Playwright login (headed) → `playwright_utils/login_utils.py`
2. `input()` asks whether to refresh the stock list → `pipeline/update_stock_list.py` → `pipeline/get_filtered_companies.py` (clicks the screener's saved "Filters" view and pages through `#main-table`; filters are **not** defined in code)
3. `cleanup_stale_data` — delete `data/<SYMBOL>/` for symbols no longer listed
4. `generate_classification_csv` — reads `data/*/income.csv` from the **previous** run → `outputs/company_classifications.csv` → `company_classifiers/`
5. `initialize_output_files` — delete `outputs/filters_results.{csv,md}`
6. `batch_process_companies` — per symbol (concurrency 2): `HttpReportsFetcher.fetch_all_reports` (skips any CSV that already exists) → `report_maker.generate_report`
7. `sort_results_csv`

## Data (files, no DB)
| What | Where | Written by |
|---|---|---|
| Stock list (symbol → name, href, sector, industry, beta) | `outputs/filtered_companies.json` | `get_filtered_companies.py` |
| List changes log | `outputs/new_companies.md` | same |
| Raw statements, 5 FY + TTM/Current columns | `data/<SYMBOL>/{income,balance-sheet,cash-flow,ratios}.csv` | `http_reports_fetcher.py` |
| Classification | `outputs/company_classifications.csv` | `generate_classifications.py` |
| Per-stock report | `data/<SYMBOL>/report.md` | `report_maker.py` |
| Summary (PASS/FAIL per check) | `outputs/filters_results.{csv,md}` | `report_maker.py` |
| Session cookie | `cookies.txt` (gitignored) | `cookie_utils.save_cookies_from_browser` |

Row names of the statements are enumerated in `enums/` (generated once from NVDA by `utils/enum_generator.py`).

## Key modules
| Path | Responsibility |
|---|---|
| `main.py`, `config.py` | Orchestration; paths relative to the repo root |
| `pipeline/http_reports_fetcher.py` | httpx download + rate limiting (15 s pause every 10 requests, 60 s on 429) |
| `pipeline/report_maker.py` | Loads CSVs, runs checks, writes reports |
| `reports_checks/basic_reports_check.py` | Current ratio, net-income trend, margins, ROE, WC vs LTD |
| `reports_checks/benjamin_graham_check.py` | Market cap, revenue, WC vs LTD, P/E, P/E×P/B or P/OCF<P/E, EPS growth |
| `reports_checks/ken_fisher_check.py` | P/S by type, net margin, EPS growth, D/E, FCF/share, R&D |
| `reports_checks/formula_helpers.py` | EPS growth, CAGR, CV, Graham product, P/OCF vs P/E |
| `company_classifiers/main.py` + `constants/sectors.py` | Type: Tech/Pharma, Defensive, High Growth, Cyclical; valuation method Graham or P/OCF |
| `playwright_utils/` | Browser lifecycle, cookies, login, popup close |
| `utils/` | DataFrame helpers, HTML table parsing, logger |

Unused: `pipeline/reports_fetcher.py`, `reports_checks/cyclical_classifier.py`, `utils/linear_regression.py` (broken), `utils/enum_generator.py` (dev tool), `playwright_utils/page_helper.py`, `quick_actions.py`.

## External services
| Service | Used for | Config (env var names only) |
|---|---|---|
| StockAnalysis.com | Screener, statements, ratios (logged-in account) | `STOCK_ANALYSIS_EMAIL`, `STOCK_ANALYSIS_PASSWORD` |

## Environments & deploy
| Env | Branch | Storage | Notes |
|---|---|---|---|
| local (WSL) | `master` | files under repo | only environment today |

## Verification commands
`uv run python -m unittest tests.verify_innovation_logic` (5 tests). No linter, no pytest yet.
