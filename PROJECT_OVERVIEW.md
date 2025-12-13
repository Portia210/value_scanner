# Project Overview: Value Scanner

**Value Scanner** is an automated financial analysis tool designed to screen stocks based on fundamental data and Benjamin Graham's investment principles. It scrapes financial statements, calculates key ratios, and generates comprehensive pass/fail reports.

## 🚀 Usage

```bash
uv run main.py
```
- **Step 1**: Prompts to update the stock list (uses Playwright to scrape StockAnalysis.com).
- **Step 2**: Cleans up stale data in `data/`.
- **Step 3**: Batches HTTP requests to fetch financial data (Income, Balance Sheet, Cash Flow, Ratios).
- **Step 4**: Generates analysis reports and logs results to `outputs/filters_results.csv`.

## 📂 Project Structure

- **`config.py`**: Central configuration for all file paths and constants.
- **`main.py`**: The orchestration entry point.
- **`pipeline/`**: Core logic modules.
    - `update_stock_list.py`: Browser automation to filtering stock lists.
    - `batch_processor.py`: Manages the concurrent fetching and processing loop.
    - `http_reports_fetcher.py`: Fetches CSV data with robust **Rate Limiting** (Batch & Breather strategy).
    - `report_maker.py`: Compiles data into Markdown reports and CSV summaries.
- **`reports_checks/`**: Financial logic.
    - `basic_reports_check.py`: Fundamental health (Profit Margin, Net Income Trend, etc.).
    - `benjamin_graham_check.py`: Advanced value investing criteria (Graham Number, P/E, Debt/Equity).
- **`outputs/`**: All generated artifacts (`filters_results.csv`, `filtered_companies.json`).
- **`data/`**: Raw CSVs and detailed `report.md` for each company.

## 🧠 Key Logic

### 1. Rate Limiting Strategy
To avoid 429 errors from the data provider, the system uses a **Batch & Breather** approach:
- Processes a small batch of requests (e.g., 10).
- Sleeps for a set duration (e.g., 15s) to allow the "token bucket" to refill.
- If a 429 is encountered, it enters a "Penalty Box" (60s sleep) before retrying.

### 2. Financial Checks
- **Benjamin Graham Criteria**:
    - **Tech Companies**: Evaluated on P/OCF < P/E and Growth (Graham Number ignored).
    - **Non-Tech**: Evaluated on Graham Number (P/E × P/B < 22).
    - **Universal**: Market Cap > $2B, Revenue > $350M, Working Capital > Debt.
- **Boolean Logic**: All checks return a tuple `(Report String, Boolean Pass/Fail)` to ensure separate visual formatting vs. logic tracking.

### 3. Modularization
The project separates concerns:
- **Inputs**: `outputs/filtered_companies.json` (Source of truth for target stocks).
- **Processing**: `pipeline/` modules handle specific phases (Update -> Fetch -> Report).
- **Outputs**: `outputs/filters_results.csv` provides a high-level summary (🟢 PASS / 🔴 FAIL) for quick scanning.
