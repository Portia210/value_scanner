# Value Scanner - Project Summary

## Overview
**Project**: `value_scanner`
**Description**: A stock analysis report generator that evaluates companies based on financial metrics and investment criteria (specifically Benjamin Graham's principles).
**Status**: Pilot phase.
**Documentation**: `report_generator_flow.md` is the primary documentation for the report generation flow and check logic.

## Key Components

### 1. Report Generation Pipeline
- **Entry Point**: `pipeline/report_maker.py` -> `generate_report(symbol)`
- **Flow**: Loads CSV data -> Runs checks -> Generates Markdown report.

### 2. Investment Checks (`reports_checks/`)
- **Basic Checks**: `basic_reports_check()` - General financial health.
- **Benjamin Graham**: `benjamin_graham_check()` - Strict value investing criteria:
    - Revenue > $350M
    - Current Ratio > 2
    - Working Capital > Long-term Debt
    - P/E < 15 (or < 25 for Tech)
    - P/E * P/B < 22
    - Consistent EPS Growth (>30% over 5 yrs)

### 3. Data Management
- **Source**: `data/{SYMBOL}/` contains `income.csv`, `balance-sheet.csv`, `ratios.csv`, `cash-flow.csv`.
- **Enums**: `enums/` folder defines row indices for these CSVs.
- **Utils**: `utils/pd_helpers.py` provides safe DataFrame access.

## Current Workspace State (Git)

### Unstaged Changes
- `main.py`: Likely entry point modifications.
- `pyproject.toml`: Dependency/config updates.
- `uv.lock`: Lock file updates.
- `test.ipynb`: Testing/Interaction notebook.
- `valid_benjamin.md`: List of stocks passing criteria involved in recent runs.

### New/Untracked Features
- **Cyclical Stocks**: Work in progress on `reports_checks/cyclical_classifier.py` and `test_cyclical_classifier.py`. This suggests a new feature to categorize or handle cyclical stocks differently is being built.

## Next Steps / Active Tasks
- Continue development of Cyclical Classifier.
- Review and commit unstaged changes in `main.py` and configuration.
- Validate report generation with recent changes.

## Important References
- `report_generator_flow.md`: Detailed system architecture.
- `existing_stocks.json`: Database of tracked stocks/sectors.
