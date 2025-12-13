from enum import Enum
import pandas as pd
import re
from enums import IncomeIndex, BalanceSheetIndex, RatiosIndex, CashFlowIndex    
from utils.get_symbol_csvs_paths import get_symbol_csvs_paths
from utils.logger import get_logger
from utils.file_handler import load_json_file
from config import FILTERS_CSV_PATH, EXISTING_STOCKS_FILE_PATH, DATA_DIR, OUTPUT_DIR
from reports_checks.basic_reports_check import basic_reports_check
from reports_checks.benjamin_graham_check import benjamin_graham_check
from reports_checks.ken_fisher_check import ken_fisher_check
from utils.pd_helpers import validate_cell_bounds, find_missing_rows, validate_row_thresholds
from config import OUTPUT_DIR # Make sure this is imported if not already

logger = get_logger()
# Cache for classifications
_CLASSIFICATIONS_CACHE = None

income_index_rows = [i.value for i in [IncomeIndex.REVENUE, IncomeIndex.NET_INCOME_GROWTH_PERCENT, IncomeIndex.OPERATING_MARGIN_PERCENT, IncomeIndex.PROFIT_MARGIN_PERCENT, IncomeIndex.EPS_DILUTED]]
balance_index_rows =  [i.value for i in [BalanceSheetIndex.WORKING_CAPITAL, BalanceSheetIndex.LONG_TERM_DEBT]]
ratio_index_rows = [i.value for i in [RatiosIndex.MARKET_CAPITALIZATION, RatiosIndex.CURRENT_RATIO, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, RatiosIndex.PE_RATIO, RatiosIndex.PB_RATIO, RatiosIndex.P_OCF_RATIO]]

def get_classifications():
    global _CLASSIFICATIONS_CACHE
    if _CLASSIFICATIONS_CACHE is not None:
        return _CLASSIFICATIONS_CACHE
    
    csv_path = OUTPUT_DIR / "company_classifications.csv"
    if not csv_path.exists():
        logger.warning(f"Classification CSV not found at {csv_path}")
        return {}
        
    try:
        df = pd.read_csv(csv_path)
        # Convert to dict of dicts: Symbol -> {Data}
        _CLASSIFICATIONS_CACHE = df.set_index("Symbol").to_dict(orient="index")
        return _CLASSIFICATIONS_CACHE
    except Exception as e:
        logger.error(f"Error loading classification CSV: {e}")
        return {}

def get_company_info(symbol):
    companies_json = load_json_file(EXISTING_STOCKS_FILE_PATH)
    if not companies_json:
        logger.warning("cannot read companies json")
        return {}
    
    if symbol not in companies_json:
        logger.info(f"{symbol} not found in list")
        return {}
    
    return companies_json[symbol]


def validate_all_dfs(income_df, balance_df, ratios_df):
    "function check for only required parameters for the calculations"
    missing_income = find_missing_rows(income_df, income_index_rows, "income df")
    missing_balance = find_missing_rows(balance_df, balance_index_rows, "balance df")
    missing_ratios = find_missing_rows(ratios_df, ratio_index_rows, "ratios df")
    full_missing_rows = missing_income + missing_balance + missing_ratios
    
    # Graceful Degradation: Allow specific rows to be missing
    ALLOWED_MISSING = {"Revenue", "Working Capital", "Operating Margin (%)"}
    missing_set = set(full_missing_rows)
    
    # Check if all missing rows are in the allowed set
    if missing_set.issubset(ALLOWED_MISSING):
        return True
        
    logger.error(f"Missing critical data: {missing_set - ALLOWED_MISSING}. Skipping report.")
    return False


def generate_report(symbol):
    logger.info(f"Compiling analysis report for: {symbol}")
    csvs_paths = get_symbol_csvs_paths(symbol)
    if csvs_paths == None:
        logger.warning(f"not all the csvs exists for {symbol}, skipping")
        return # Added return to stop execution if CSVs are missing completely
        
    company_info = get_company_info(symbol)
    sector = company_info.get("sector", "Unknown")
    industry = company_info.get("industry", "Unknown")
    beta = company_info.get("beta")

    paths = get_symbol_csvs_paths(symbol)
    income_df = pd.read_csv(paths["income"], index_col=0)
    balance_df = pd.read_csv(paths["balance-sheet"], index_col=0)
    ratios_df = pd.read_csv(paths["ratios"], index_col=0)
    
    # Enforce validation with graceful degradation
    if not validate_all_dfs(income_df, balance_df, ratios_df):
        return
    

    
    # sort years cols to filter only FY 20{/d/d}
    last_5_years_cols = [col for col in income_df.columns if re.match(r'FY 20\d{2}', col)][:5]
    last_5_years_cols.sort(reverse=True)
    income_df_sub = income_df.reindex(income_index_rows)
    balance_df_sub = balance_df.reindex(balance_index_rows)
    ratios_df_sub = ratios_df.reindex(ratio_index_rows)

    # Replace NaN with '-' for better markdown display
    income_df_sub = income_df_sub.fillna('-')
    balance_df_sub = balance_df_sub.fillna('-')
    ratios_df_sub = ratios_df_sub.fillna('-')

    # Retrieve Pre-Calculated Classification
    classifications = get_classifications()
    company_data = classifications.get(symbol, {})
    
    # Default fallback if not found
    company_type = company_data.get("Type", "Defensive") 
    valuation_method = company_data.get("Valuation Method", "Graham")
    reasons = company_data.get("Reasons", "No classification data found")
    sector_from_csv = company_data.get("Sector", sector)
    industry_from_csv = company_data.get("Industry", industry)

    # Reconstruct dictionary for checks
    classification_res = {
        "type": company_type,
        "valuation_method": valuation_method,
        "reasons": reasons.split(", ") if isinstance(reasons, str) else [],
        "sector": sector_from_csv,
        "industry": industry_from_csv
    }

    md_file_txt = f"""# {symbol}
**Sector:** {sector_from_csv} | **Industry:** {industry_from_csv}
**Type:** {company_type} ({valuation_method})
**Reasoning:** {reasons}

---

## Financial Summary
\n**Income statement**\n{income_df_sub.to_markdown()}
\n\n**balance statment**\n{balance_df_sub.to_markdown()}
\n\n**ratios statment**\n{ratios_df_sub.to_markdown()}
"""
    # Add basic reports check (passing classification result)
    basic_report_str, basic_passed = basic_reports_check(symbol, income_df, balance_df, ratios_df, last_5_years_cols, classification_res)
    md_file_txt += basic_report_str

    # Add Benjamin Graham investment criteria check (passing classification result)
    graham_report_str, graham_passed = benjamin_graham_check(symbol, income_df, balance_df, ratios_df, last_5_years_cols, classification_res)
    md_file_txt += graham_report_str

    # Add Ken Fisher Super Stocks check
    fisher_report_str, fisher_passed = ken_fisher_check(symbol, income_df, balance_df, ratios_df, last_5_years_cols, classification_res)
    md_file_txt += fisher_report_str
    
    # Log results to CSV
    try:
        results_file = FILTERS_CSV_PATH
        file_exists = results_file.exists()
             
        with open(results_file, "a") as f:
            if not file_exists:
                f.write("Report Path,Symbol,Basic Reports Check,Benjamin Graham Check,Ken Fisher Check\n")
            
            basic_res = "🟢 PASS" if basic_passed else "🔴 FAIL"
            graham_res = "🟢 PASS" if graham_passed else "🔴 FAIL"
            fisher_res = "🟢 PASS" if fisher_passed else "🔴 FAIL"
            
            # Storing relative path in CSV. 
            # The Markdown Dashboard generator will use this to create clickable [Link](path).
            relative_report_path = f"data/{symbol}/report.md"
            
            f.write(f"{relative_report_path},{symbol},{basic_res},{graham_res},{fisher_res}\n")
    except Exception as e:
        logger.error(f"Failed to write to {results_file} for {symbol}: {e}")

    # User Request: Minimalist Markdown Dashboard (Same logic as CSV)
    # Appending row-by-row to outputs/filters_results.md
    try:
        md_dashboard_path = OUTPUT_DIR / "filters_results.md"
        md_exists = md_dashboard_path.exists()
        
        with open(md_dashboard_path, "a") as f:
            if not md_exists:
                f.write("# Value Scanner Results\n\n")
                f.write("| Report Link | Symbol | Basic Check | Graham Check | Fisher Check |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            
            # Simple clickable relative link: [View](../data/SYM/report.md)
            # Context: Scan results is in outputs/, report is in data/
            relative_link = f"[📄 View](../data/{symbol}/report.md)"
            
            # Reusing the status emoticons from CSV block
            md_row = f"| {relative_link} | {symbol} | {basic_res} | {graham_res} | {fisher_res} |\n"
            f.write(md_row)
            
    except Exception as e:
        logger.error(f"Failed to write to markdown dashboard for {symbol}: {e}")

    report_path = DATA_DIR / symbol / "report.md"
    with open(report_path, "w") as f:
        f.write(md_file_txt)

    


    
if __name__ == "__main__":
    generate_report("AIT")