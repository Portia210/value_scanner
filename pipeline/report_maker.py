from enum import Enum
import pandas as pd
import re
from enums import IncomeIndex, BalanceSheetIndex, RatiosIndex, CashFlowIndex    
from utils.get_symbol_csvs_paths import get_symbol_csvs_paths
from utils.logger import get_logger
from utils.file_handler import load_json_file
from config import EXISTING_STOCKS_FILE_PATH

logger = get_logger()

income_index_rows = [i.value for i in [IncomeIndex.NET_INCOME_GROWTH_PERCENT, IncomeIndex.OPERATING_MARGIN_PERCENT, IncomeIndex.PROFIT_MARGIN_PERCENT]]
balance_index_rows =  [i.value for i in [BalanceSheetIndex.WORKING_CAPITAL]]
ratio_index_rows = [i.value for i in [RatiosIndex.CURRENT_RATIO, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, RatiosIndex.PE_RATIO, RatiosIndex.PB_RATIO, RatiosIndex.P_OCF_RATIO]]
 


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

    
def check_missing_rows_in_df(df, required_rows: list, df_name: str = None) -> list:
    "required rows is a list of enum members"
    missing_rows = [row for row in required_rows if row not in df.index]
    if missing_rows:
        t = f"for {df_name}" if df_name else ""
        logger.warning(f"missing_rows {t}: {missing_rows}")
        return missing_rows
    return []

def validate_all_dfs(income_df, balance_df, ratios_df):
    "function check for only required parameters for the calculations"
    missing_income = check_missing_rows_in_df(income_df, income_index_rows, "income df")
    missing_balance = check_missing_rows_in_df(balance_df, balance_index_rows, "balace df")
    missing_ratios = check_missing_rows_in_df(ratios_df, ratio_index_rows, "ratios df")
    full_missing_rows = missing_income + missing_balance + missing_ratios
    if len(full_missing_rows) == 0:
        return True
    return False

def check_for_long_term_debt(balance_df):
    if check_missing_rows_in_df(balance_df, [BalanceSheetIndex.LONG_TERM_DEBT.value], "balance df"):
        return True
    return False
    
def check_row_data(df: pd.DataFrame, row_index: Enum, wanted_cols=None, min_avg=0, min_sum=0):
    cols = wanted_cols if wanted_cols else df.columns
    try:
        net_income_growth_row = df.loc[row_index.value, cols]
        # Calculate sum, average (mean), and median
        total = net_income_growth_row.sum()
        avg = net_income_growth_row.mean()  # mean() is the same as average
        if total > min_sum and avg > min_avg:
            return True
        else:
            logger.info("not meet up standarts")
            return False
            
    except Exception as e:
        logger.error(e)

def generate_report(symbol):
    csvs_paths = get_symbol_csvs_paths(symbol)
    if csvs_paths == None:
        logger.warning(f"not all the csvs exists for {symbol}, skipping")
        
    company_secotr = get_symbol_sector(symbol)
    paths = get_symbol_csvs_paths(symbol)
    income_df = pd.read_csv(paths["income"], index_col=0)
    balance_df = pd.read_csv(paths["balance-sheet"], index_col=0)
    ratios_df = pd.read_csv(paths["ratios"], index_col=0)
    logger.info(income_df.info())
    
    if not validate_all_dfs(income_df, balance_df, ratios_df):
        logger.warning(f"not all df valid for {symbol}, skipping")
        return
    
    long_term_debt_exist = check_for_long_term_debt(balance_df)
    logger.info(f"is long term debt exist {long_term_debt_exist}")
    
    # sort years cols to filter only FY 20{/d/d}
    last_5_years_cols = [col for col in income_df.columns if re.match(r'FY 20\d{2}', col)][:5]
    last_5_years_cols.sort(reverse=True)
    logger.info(f"last 5 years {last_5_years_cols}")
    logger.info(f"last 5 years {type(last_5_years_cols)}")
    first_lesson_filters(symbol, income_df, balance_df, ratios_df, last_5_years_cols)

    
def first_lesson_filters(sybmol, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list):
    # for row in [IncomeIndex.NET_INCOME_GROWTH_PERCENT, IncomeIndex.OPERATING_MARGIN_PERCENT, IncomeIndex.PROFIT_MARGIN_PERCENT]:
    # # meet_up_standard = check_row_data(income_df, row, last_5_years_cols, min_avg=15, min_sum=60)
    # # if not meet_up_standard:
    #     pass    
    income_df_sub = income_df.loc[income_index_rows]
    balance_df_sub = balance_df.loc[balance_index_rows]
    ratios_df_sub = ratios_df.loc[ratio_index_rows]

    full_md_file = f"""summary for {sybmol}
    \n\n**Income statement**\n{income_df_sub.to_markdown()}
    \n\n**balance statment**\n{balance_df_sub.to_markdown()}
    \n\n**ratios statment**\n{ratios_df_sub.to_markdown()}
    """
    
    with open("short_report.md", "w") as f:
        f.write(full_md_file)
    
    
if __name__ == "__main__":
    generate_report("NVDA")