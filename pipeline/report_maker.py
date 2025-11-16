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

def has_long_term_debt(balance_df):
    """Returns True if Long-Term Debt row exists in the DataFrame"""
    if check_missing_rows_in_df(balance_df, [BalanceSheetIndex.LONG_TERM_DEBT.value], "balance df"):
        return False  # Missing means no debt data
    return True  # Row exists
    
def check_row_data(df: pd.DataFrame, row_index: Enum, years_cols: list, min_avg=0, min_sum=0):
    cols = years_cols if years_cols else df.columns
    try:
        row = df.loc[row_index.value, cols]
        # Calculate sum, average (mean), and median
        total = row.sum()
        avg = row.mean()  # mean() is the same as average
        if total >= min_sum and avg >= min_avg:
            pass_check = True
        else:
            pass_check =  False
        return f"**valid?** {pass_check}, avarage: {avg:.2f}, total: {total:.2f}"
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
    
    if not validate_all_dfs(income_df, balance_df, ratios_df):
        logger.warning(f"not all df valid for {symbol}, skipping")
        return
    

    # sort years cols to filter only FY 20{/d/d}
    last_5_years_cols = [col for col in income_df.columns if re.match(r'FY 20\d{2}', col)][:5]
    last_5_years_cols.sort(reverse=True)
    first_lesson_filters(symbol, income_df, balance_df, ratios_df, last_5_years_cols)

    
def first_lesson_filters(sybmol, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list):
    # for row in [IncomeIndex.NET_INCOME_GROWTH_PERCENT, IncomeIndex.OPERATING_MARGIN_PERCENT, IncomeIndex.PROFIT_MARGIN_PERCENT]:
    # # meet_up_standard = check_row_data(income_df, row, last_5_years_cols, min_avg=15, min_sum=60)
    # # if not meet_up_standard:
    #     pass    
    income_df_sub = income_df.loc[income_index_rows]
    balance_df_sub = balance_df.loc[balance_index_rows]
    ratios_df_sub = ratios_df.loc[ratio_index_rows]
    net_income_check = check_row_data(income_df, IncomeIndex.NET_INCOME_GROWTH_PERCENT, last_5_years_cols, 10, 35)
    operating_margin_chceck = check_row_data(income_df, IncomeIndex.OPERATING_MARGIN_PERCENT, last_5_years_cols, 10, 35)
    profit_margin_check = check_row_data(income_df, IncomeIndex.PROFIT_MARGIN_PERCENT, last_5_years_cols, 10, 35)
    roe_check = check_row_data(ratios_df, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, last_5_years_cols, 15, 50)
    
    if has_long_term_debt(balance_df):
        # logger.info("there is a debt")
        working_capital = balance_df.loc[BalanceSheetIndex.WORKING_CAPITAL.value, last_5_years_cols[0]]
        long_term_debt = balance_df.loc[BalanceSheetIndex.LONG_TERM_DEBT.value, last_5_years_cols[0]]
        working_capital_greater_than_debt = working_capital >= long_term_debt
        capital_vs_debt = f"**valid?**: {working_capital_greater_than_debt}, working capital minus debt is ({working_capital} - {long_term_debt}) = {(working_capital - long_term_debt):.2f}"
    else:
        capital_vs_debt = f"**valid?**: {True}, There is no long term debt"



    full_md_file = f"""summary for {sybmol}
\n\n**Income statement**\n{income_df_sub.to_markdown()}
\n\n**balance statment**\n{balance_df_sub.to_markdown()}
\n\n**ratios statment**\n{ratios_df_sub.to_markdown()}
\n\n- net income:  {net_income_check}
- operting margin:  {operating_margin_chceck}
- profit margin:  {profit_margin_check}
- working capital vs long-term debt:  {capital_vs_debt}
- ROE check:  {roe_check}
    """
    
    with open("short_report.md", "w") as f:
        f.write(full_md_file)
    
    
if __name__ == "__main__":
    generate_report("AIT")