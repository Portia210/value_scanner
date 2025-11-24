# Report Generator Flow Documentation

## Overview

This document describes the stock analysis report generation system and the investment criteria checks implemented in the Value Scanner project.

## Report Generation Structure

### Main Components

1. **Pipeline Entry Point**: `pipeline/report_maker.py`
   - Main function: `generate_report(symbol)`
   - Loads CSV data for the specified stock symbol
   - Generates markdown reports with financial analysis

2. **Report Checks Module**: `reports_checks/`
   - `basic_reports_check()` - General financial health metrics
   - `benjamin_graham_check()` - Benjamin Graham investment criteria

3. **Helper Utilities**: `utils/pd_helpers.py`
   - Reusable pandas DataFrame validation functions
   - Modular design for checking financial metrics

### Data Sources

The report generator reads CSV files from `data/{SYMBOL}/`:
- `income.csv` - Income statement data
- `balance-sheet.csv` - Balance sheet data
- `ratios.csv` - Financial ratios
- `cash-flow.csv` - Cash flow statement

### Report Output

- **Output File**: `data/{SYMBOL}/report.md`
- **Content Structure**:
  1. Company header (symbol and sector)
  2. Financial summary tables (Income, Balance Sheet, Ratios)
  3. Basic Reports Check results
  4. Benjamin Graham Investment Criteria Check results

---

## Benjamin Graham Investment Criteria

The `benjamin_graham_check()` function implements the following investment requirements:

### 1. Revenue Threshold
**Requirement**: Revenue > $350M

- Checks the most recent fiscal year revenue
- Ensures the company has sufficient scale and stability
- **Pass Criteria**: Annual revenue exceeds $350 million

### 2. Current Ratio Check
**Requirement**: Current Ratio ≥ 2

- Formula: `Current Assets / Current Liabilities`
- Measures short-term liquidity and ability to meet obligations
- **Pass Criteria**: Ratio must be at least 2.0
- Indicates the company has twice as many current assets as current liabilities

### 3. Financial Strength
**Requirement**: Working Capital > Long-term Debt

- Formula: `Working Capital - Long-term Debt > 0`
- Working Capital = Current Assets - Current Liabilities
- Tests financial stability and debt management
- **Pass Criteria**: Working capital exceeds long-term debt obligations
- Special case: If no long-term debt exists, automatically passes

### 4. Valuation Checks

#### 4a. P/E Ratio Range
**Requirement**:
- Regular companies: `5 < P/E < 15`
- Technology companies: `5 < P/E < 25`

- P/E Ratio = Price / Earnings per Share
- Avoids overvalued stocks (high P/E) and risky distressed stocks (very low P/E)
- Tech companies get higher threshold due to growth premium
- **Technology Detection**: Checks company sector for keywords: Technology, Software, Internet, Semiconductor, Computer, Tech

#### 4b. Graham Number Check
**Requirement**: `P/E × P/B < 22`

- P/B Ratio = Price / Book Value (Shareholder Equity)
- Combined valuation metric from Benjamin Graham's formula
- **Pass Criteria**: Product must be less than 22
- Applies to all companies (both regular and tech)

#### 4c. Tech Company P/OCF Check
**Requirement**: `P/OCF < P/E` (only for tech companies if P/E is valid)

- P/OCF Ratio = Price / Operating Cash Flow
- For tech companies, validates cash generation relative to earnings
- Only checked if:
  1. Company is identified as tech
  2. P/E ratio is within valid range
- **Pass Criteria**: P/OCF must be lower than P/E ratio

### 5. Growth Check
**Requirement**: 30% EPS growth over 5 years

- Uses Earnings Per Share (Diluted) data
- **Calculation Method**:
  1. Take average EPS of first 2 years (oldest) from 5-year period
  2. Take average EPS of last 2 years (most recent) from 5-year period
  3. Calculate growth percentage: `((last_2yr_avg - first_2yr_avg) / first_2yr_avg) × 100`
- **Pass Criteria**: Growth must be ≥ 30%
- Ensures consistent earnings growth and company momentum

---

## Key Implementation Files

**For AI Agents**: Always read these files to understand current implementation and monitor changes:

1. **`utils/pd_helpers.py`**
   - Contains all reusable validation helper functions
   - Modular functions for checking DataFrame cells, rows, and ranges
   - Benjamin Graham-specific validation utilities

2. **`utils/formatting.py`**
   - Visual formatting utilities for report output
   - `format_valid()` function: Adds colored indicators (🟢 PASS / 🔴 FAIL) to validation messages
   - Used consistently across all report check functions

3. **`reports_checks/benjamin_graham_check.py`**
   - Main implementation of Benjamin Graham investment criteria
   - Contains the complete check logic and tech company detection
   - Integrates all helper functions from `pd_helpers.py`
   - Uses `format_valid()` for colored output

4. **`reports_checks/basic_reports_check.py`**
   - General financial health metrics validation
   - Basic checks for margins, ratios, and working capital
   - Uses `format_valid()` for colored output

5. **`pipeline/report_maker.py`**
   - Report generation orchestration
   - Loads data, calls check functions, generates markdown output
   - Entry point: `generate_report(symbol)` function

6. **`enums/` folder**
   - `income_index.py`, `balance_sheet_index.py`, `ratios_index.py`, `cash_flow_index.py`
   - Enum definitions for CSV row indices
   - Used to access financial data consistently across the codebase

---

## Report Formatting

### Visual Indicators

All validation results use colored indicators for easy scanning:

- **🟢 PASS** - Criterion is satisfied
- **🔴 FAIL** - Criterion is not satisfied
- **N/A** - Check not applicable (e.g., tech-specific checks for regular companies)

The `format_valid()` function in `utils/formatting.py` handles this consistently across all reports.

### Missing Data Handling

- Reports generate even when data is missing (no longer skipped)
- Missing rows/cells show as `🔴 FAIL` with clear error messages
- Example: `🔴 **FAIL**, row 'Revenue' not found in data`
- NaN values in tables display as `-` for cleaner output

---

## Usage Example

```python
from pipeline.report_maker import generate_report

# Generate report for a stock symbol
generate_report("AIT")

# Output: short_report.md containing:
# - Financial statement summaries
# - Basic reports check results
# - Benjamin Graham investment criteria analysis
```

---

## Implementation Notes

### Modular Design
- All validation functions are reusable and independent
- Helper functions return consistent tuple format: `(bool, str)`
- Each check is self-contained with error handling

### Tech Company Detection
- Reads sector from `existing_stocks.json`
- Keywords: Technology, Software, Internet, Semiconductor, Computer, Tech
- Case-insensitive matching

### Data Requirements
- Minimum 5 years of historical data for growth calculations
- All checks use most recent fiscal year (FY) data unless specified
- Columns must match format: `FY 20XX` (e.g., "FY 2024", "FY 2023")

### Error Handling
- All helper functions include try-except blocks with KeyError handling
- Returns descriptive error messages: `row 'X' not found in data`
- Logs warnings for missing data via logger utility
- Dollar signs escaped (`\$`) to prevent markdown LaTeX interpretation
