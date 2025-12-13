# Project Overview: Value Scanner

**Value Scanner** is an automated financial analysis tool designed to screen stocks based on fundamental data and Benjamin Graham's investment principles. It scrapes financial statements, calculates key ratios, and generates comprehensive pass/fail reports.

## 🚀 Usage

```bash
uv run main.py
```
- **Step 1**: Prompts to update the stock list (uses Playwright to scrape StockAnalysis.com).
- **Step 2**: Cleans up stale data in `data/`.
- **Step 3**: Generates **Advanced Company Classifications** (Source of Truth CSV).
- **Step 4**: Batches HTTP requests to fetch financial data (Income, Balance Sheet, Cash Flow, Ratios).
- **Step 5**: Generates analysis reports and logs results to `outputs/filters_results.csv`.

## 📂 Project Structure

- **`config.py`**: Central configuration for all file paths and constants.
- **`main.py`**: The orchestration entry point.
- **`pipeline/`**: Core logic modules.
    - `update_stock_list.py`: Browser automation to filtering stock lists.
    - `batch_processor.py`: Manages the concurrent fetching and processing loop.
    - `http_reports_fetcher.py`: Fetches CSV data with robust **Rate Limiting** (Batch & Breather strategy).
    - `report_maker.py`: Compiles reports, consuming `outputs/company_classifications.csv` for logic branching.
- **`company_classifiers/`**: **Advanced Classification Engine**.
    - `main.py`: Orchestrator (Tech, Pharma, Growth, Cyclical rules).
    - `generate_classifications.py`: Batch script to classify all companies before reporting.
    - `tech.py`, `pharma.py`, `growth.py`, `cyclical.py`: Granular logic modules.
- **`reports_checks/`**: Financial logic.
    - `basic_reports_check.py`: Fundamental health (Profit Margin, Net Income Trend, etc.).

    - `benjamin_graham_check.py`: Advanced value investing criteria (Graham Number, P/E, Debt/Equity).
    - `ken_fisher_check.py`: **"Super Stocks" Strategy** (Price-to-Sales, Innovation, Margins).
- **`outputs/`**: All generated artifacts (`filters_results.csv`, `filtered_companies.json`).
- **`data/`**: Raw CSVs and detailed `report.md` for each company.

## 🧠 Key Logic

### 1. Rate Limiting Strategy
To avoid 429 errors from the data provider, the system uses a **Batch & Breather** approach:
- Processes a small batch of requests (e.g., 10).
- Sleeps for a set duration (e.g., 15s) to allow the "token bucket" to refill.
- If a 429 is encountered, it enters a "Penalty Box" (60s sleep) before retrying.

### 2. Advanced Classification Engine (New)
A robust 4-tier hierarchy classifies companies to determine the correct valuation method:
1.  **Tech/Pharma**: Always "Tech/Growth" (P/OCF Check).
2.  **Defensive Sectors** (Utilities, Staples, Financials):
    - Default: "Defensive" (Graham Check).
    - Upgrade: "High Growth" if **3-Year CAGR > 20%** AND **Low Volatility**.
    - Trap: "Cyclical" if High Growth but High Volatility.
3.  **Cyclical Sectors**: Default "Cyclical" (P/OCF Check).
4.  **The Rest**: Fallback.

**Key Features**:
- **3-Year CAGR**: Replaces volatile YoY growth.
- **Volatility Trap**: Forces volatile growers into Cyclical buckets.
- **Insurance Hard-Lock**: Prevents financial companies from being misclassified as Growth.

### 3. Financial Checks
- **Benjamin Graham Criteria**:
    - **Valuation Method**: Dynamically selected based on Classification (Graham vs P/OCF).
    - **Tech/Growth**: P/OCF < 25, P/E < 40.
    - **Defensive**: Graham Number (P/E × P/B < 22.5).
- **Ken Fisher "Super Stocks"**:
    - **Valuation**: P/S < 1.5 (General) | P/S < 0.8 (Cyclical/Staples) | Industrial Exception (P/E < 25 OR Graham).
    - **Innovation**: R&D Intensity > 10% (Tech Only).
    - **Margins**: > 8% (General) | > 15% (Tech).
- **Boolean Logic**: All checks return a tuple `(Report String, Boolean Pass/Fail)` to ensure separate visual formatting vs. logic tracking.

### 4. Modularization
The project separates concerns:
- **Inputs**: `outputs/filtered_companies.json` (Source of truth for target stocks).
- **Processing**: `pipeline/` modules handle specific phases (Update -> Fetch -> Report).
- **Outputs**: `outputs/filters_results.csv` provides a high-level summary (🟢 PASS / 🔴 FAIL) for quick scanning.
