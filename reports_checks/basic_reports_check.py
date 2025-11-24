import pandas as pd
from enums import IncomeIndex, RatiosIndex, BalanceSheetIndex
from utils.pd_helpers import check_cell_data, check_missing_rows_in_df, check_row_data, get_cell_value_safe
from utils.formatting import format_valid

def basic_reports_check(symbol, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list):
    # Define requirements
    current_ratio_min = 2
    net_income_min_avg = 2
    net_income_min_sum = 10
    operating_margin_min_avg = 2
    operating_margin_min_sum = 10
    profit_margin_min_avg = 2
    profit_margin_min_sum = 10
    roe_min_avg = 15
    roe_min_sum = 50

    current_ratio_check = check_cell_data(ratios_df, RatiosIndex.CURRENT_RATIO, last_5_years_cols[0], current_ratio_min)
    net_income_check = check_row_data(income_df, IncomeIndex.NET_INCOME_GROWTH_PERCENT, last_5_years_cols, net_income_min_avg, net_income_min_sum)
    operating_margin_check = check_row_data(income_df, IncomeIndex.OPERATING_MARGIN_PERCENT, last_5_years_cols, operating_margin_min_avg, operating_margin_min_sum)
    profit_margin_check = check_row_data(income_df, IncomeIndex.PROFIT_MARGIN_PERCENT, last_5_years_cols, profit_margin_min_avg, profit_margin_min_sum)
    roe_check = check_row_data(ratios_df, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, last_5_years_cols, roe_min_avg, roe_min_sum)

    working_capital = get_cell_value_safe(balance_df, BalanceSheetIndex.WORKING_CAPITAL, last_5_years_cols[0])
    long_term_debt = get_cell_value_safe(balance_df, BalanceSheetIndex.LONG_TERM_DEBT, last_5_years_cols[0])

    if long_term_debt is None or long_term_debt == 0:
        capital_vs_debt = format_valid(True, f"**valid?**: True, No long-term debt")
    elif working_capital is None:
        capital_vs_debt = format_valid(False, f"**valid?**: False, Working capital data unavailable")
    else:
        working_capital_greater_than_debt = working_capital >= long_term_debt
        capital_vs_debt = format_valid(working_capital_greater_than_debt, f"**valid?**: {working_capital_greater_than_debt}, working capital minus debt is ({working_capital:.2f} - {long_term_debt:.2f}) = {(working_capital - long_term_debt):.2f}")

    # Apply formatting to all checks
    current_ratio_check = format_valid("True" in current_ratio_check, current_ratio_check)
    net_income_check = format_valid("True" in net_income_check, net_income_check)
    operating_margin_check = format_valid("True" in operating_margin_check, operating_margin_check)
    profit_margin_check = format_valid("True" in profit_margin_check, profit_margin_check)
    roe_check = format_valid("True" in roe_check, roe_check)

    return f"""
\n\n> **Basic Reports Check**
- current ratio (≥ {current_ratio_min}): {current_ratio_check}
- net income (avg ≥ {net_income_min_avg}%, total ≥ {net_income_min_sum}%):  {net_income_check}
- operating margin (avg ≥ {operating_margin_min_avg}%, total ≥ {operating_margin_min_sum}%):  {operating_margin_check}
- profit margin (avg ≥ {profit_margin_min_avg}%, total ≥ {profit_margin_min_sum}%):  {profit_margin_check}
- working capital vs long-term debt (WC ≥ debt):  {capital_vs_debt}
- ROE (avg ≥ {roe_min_avg}%, total ≥ {roe_min_sum}%):  {roe_check}
    """
