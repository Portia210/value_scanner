import pandas as pd
from enums import IncomeIndex, RatiosIndex, BalanceSheetIndex
from utils.pd_helpers import check_cell_data, check_missing_rows_in_df, check_row_data
from utils.formatting import format_valid

def basic_reports_check(symbol, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list):

    current_ratio_check = check_cell_data(ratios_df, RatiosIndex.CURRENT_RATIO, last_5_years_cols[0], 2)
    net_income_check = check_row_data(income_df, IncomeIndex.NET_INCOME_GROWTH_PERCENT, last_5_years_cols, 10, 35)
    operating_margin_check = check_row_data(income_df, IncomeIndex.OPERATING_MARGIN_PERCENT, last_5_years_cols, 10, 35)
    profit_margin_check = check_row_data(income_df, IncomeIndex.PROFIT_MARGIN_PERCENT, last_5_years_cols, 10, 35)
    roe_check = check_row_data(ratios_df, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, last_5_years_cols, 15, 50)

    if check_missing_rows_in_df(balance_df, [BalanceSheetIndex.LONG_TERM_DEBT.value], "balance df"):
        working_capital = balance_df.loc[BalanceSheetIndex.WORKING_CAPITAL.value, last_5_years_cols[0]]
        long_term_debt = balance_df.loc[BalanceSheetIndex.LONG_TERM_DEBT.value, last_5_years_cols[0]]
        working_capital_greater_than_debt = working_capital >= long_term_debt
        capital_vs_debt = format_valid(working_capital_greater_than_debt, f"**valid?**: {working_capital_greater_than_debt}, working capital minus debt is ({working_capital} - {long_term_debt}) = {(working_capital - long_term_debt):.2f}")
    else:
        capital_vs_debt = format_valid(True, f"**valid?**: {True}, There is no long term debt")

    # Apply formatting to all checks
    current_ratio_check = format_valid("True" in current_ratio_check, current_ratio_check)
    net_income_check = format_valid("True" in net_income_check, net_income_check)
    operating_margin_check = format_valid("True" in operating_margin_check, operating_margin_check)
    profit_margin_check = format_valid("True" in profit_margin_check, profit_margin_check)
    roe_check = format_valid("True" in roe_check, roe_check)

    return f"""
\n\n> **Basic Reports Check**
- current ratio: {current_ratio_check}
- net income:  {net_income_check}
- operating margin:  {operating_margin_check}
- profit margin:  {profit_margin_check}
- working capital vs long-term debt:  {capital_vs_debt}
- ROE check:  {roe_check}
    """
