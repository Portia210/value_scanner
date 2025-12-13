from enum import Enum
import pandas as pd
import re
from enums import IncomeIndex, BalanceSheetIndex, RatiosIndex, CashFlowIndex    
from utils.get_symbol_csvs_paths import get_symbol_csvs_paths
from utils.logger import get_logger
from utils.file_handler import load_json_file
from config import EXISTING_STOCKS_FILE_PATH
from reports_checks import basic_reports_check, benjamin_graham_check
from utils.pd_helpers import validate_cell_bounds, find_missing_rows, validate_row_thresholds

logger = get_logger()

income_index_rows = [i.value for i in [IncomeIndex.REVENUE, IncomeIndex.NET_INCOME_GROWTH_PERCENT, IncomeIndex.OPERATING_MARGIN_PERCENT, IncomeIndex.PROFIT_MARGIN_PERCENT, IncomeIndex.EPS_DILUTED]]
balance_index_rows =  [i.value for i in [BalanceSheetIndex.WORKING_CAPITAL, BalanceSheetIndex.LONG_TERM_DEBT]]
ratio_index_rows = [i.value for i in [RatiosIndex.MARKET_CAPITALIZATION, RatiosIndex.CURRENT_RATIO, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, RatiosIndex.PE_RATIO, RatiosIndex.PB_RATIO, RatiosIndex.P_OCF_RATIO]]
 


def get_symbol_sector(symbol):
    companies_json = load_json_file(EXISTING_STOCKS_FILE_PATH)
    if not companies_json:
        logger.warning("cannot read companies json")
    
    if not symbol in companies_json:
        logger.info(f"{symbol} not found in list")
    
    try:
        return companies_json[symbol]["sector"]
    except Exception as e:
        logger.error(e)

    


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
        
    company_secotr = get_symbol_sector(symbol)
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

    md_file_txt = f"""# {symbol}
**Sector:** {company_secotr or 'Unknown'}

---

## Financial Summary
\n**Income statement**\n{income_df_sub.to_markdown()}
\n\n**balance statment**\n{balance_df_sub.to_markdown()}
\n\n**ratios statment**\n{ratios_df_sub.to_markdown()}
"""
    # Add basic reports check
    basic_report_str, basic_passed = basic_reports_check(symbol, income_df, balance_df, ratios_df, last_5_years_cols, company_secotr)
    md_file_txt += basic_report_str

    # Add Benjamin Graham investment criteria check
    graham_report_str, graham_passed = benjamin_graham_check(symbol, income_df, balance_df, ratios_df, last_5_years_cols, company_secotr)
    md_file_txt += graham_report_str
    
    # Log results to CSV
    try:
        results_file = "filters_results.csv"
        file_exists = False
        try:
             with open(results_file, "r") as f:
                 file_exists = True
        except FileNotFoundError:
             pass
             
        with open(results_file, "a") as f:
            if not file_exists:
                f.write("Symbol,Basic Reports Check,Benjamin Graham Check\n")
            
            basic_res = "🟢" if basic_passed else "🔴"
            graham_res = "🟢" if graham_passed else "🔴"
            
            f.write(f"{symbol},{basic_res},{graham_res}\n")
    except Exception as e:
        logger.error(f"Failed to write to {results_file} for {symbol}: {e}")

    with open(f"data/{symbol}/report.md", "w") as f:
        f.write(md_file_txt)

    


    
if __name__ == "__main__":
    generate_report("AIT")