import pandas as pd
from enums import IncomeIndex, RatiosIndex, BalanceSheetIndex
from utils.pd_helpers import validate_cell_bounds, validate_row_thresholds, get_cell_safe, get_row_safe
from utils.formatting import format_valid
from utils.logger import get_logger
logger = get_logger()

def basic_reports_check(symbol, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list, company_sector: str = None):
    most_recent_year = last_5_years_cols[0]

    # Define requirements
    current_ratio_min = 2
    
    # Net Income: Positive Trend Check (Last 2 Years Avg > First 2 Years Avg)
    # net_income_min_avg = 0  <-- Removing old check
    
    # Profit Margin: Sector-based thresholds
    # Tech/Pharma/Healthcare > 15%, usage of "Communication Services" implies Tech often too
    # Others > 8%
    
    high_margin_sectors = {'Technology', 'Communication Services', 'Healthcare'} # Healthcare covers Pharma
    if company_sector and company_sector in high_margin_sectors:
        profit_margin_min_avg = 15
    else:
        profit_margin_min_avg = 8
        
    operating_margin_min_avg = 0 # kept as positive check? User didn't specify change, only "Revenue Gross -> Operating Margin" mentioned in Hebrew but without number. Assuming keeping > 0.
    roe_min_avg = 15

    # Checks
    # Checks - Capture RAW strings first
    current_ratio_raw = validate_cell_bounds(ratios_df, RatiosIndex.CURRENT_RATIO, most_recent_year, current_ratio_min)
    
    # Net Income Trend Logic
    ni_row = get_row_safe(income_df, IncomeIndex.NET_INCOME, last_5_years_cols)
    if ni_row is not None and len(ni_row) >= 4:
         recent_avg = ni_row.iloc[:2].mean()
         oldest_avg = ni_row.iloc[-2:].mean()
         
         is_positive_trend = recent_avg > oldest_avg
         # Create raw message manually to match format expected by format_valid if needed, 
         # but actually we can just pass the bool to format_valid. 
         # But we need the message text.
         net_income_raw = f"**valid?**: {is_positive_trend}, Recent Avg ({recent_avg:.2f}) > Oldest Avg ({oldest_avg:.2f})"
         net_income_pass = is_positive_trend
    else:
         net_income_raw = "**valid?**: False, insufficient data for trend check"
         net_income_pass = False

    
    operating_margin_raw = validate_row_thresholds(income_df, IncomeIndex.OPERATING_MARGIN_PERCENT, last_5_years_cols, operating_margin_min_avg)
    profit_margin_raw = validate_row_thresholds(income_df, IncomeIndex.PROFIT_MARGIN_PERCENT, last_5_years_cols, profit_margin_min_avg)
    roe_raw = validate_row_thresholds(ratios_df, RatiosIndex.RETURN_ON_EQUITY_ROE_PERCENT, last_5_years_cols, roe_min_avg)

    working_capital = get_cell_safe(balance_df, BalanceSheetIndex.WORKING_CAPITAL, most_recent_year)
    long_term_debt = get_cell_safe(balance_df, BalanceSheetIndex.LONG_TERM_DEBT, most_recent_year)

    if long_term_debt is None or long_term_debt == 0:
        capital_vs_debt_pass = True
        capital_vs_debt_raw = f"**valid?**: True, No long-term debt"
    elif working_capital is None:
        capital_vs_debt_pass = False
        capital_vs_debt_raw = f"**valid?**: False, Working capital data unavailable"
    else:
        capital_vs_debt_pass = working_capital >= long_term_debt
        capital_vs_debt_raw = f"**valid?**: {capital_vs_debt_pass}, working capital minus debt is ({working_capital:.2f} - {long_term_debt:.2f}) = {(working_capital - long_term_debt):.2f}"
        
    # Parse booleans from RAW strings (if not already calculated)
    # Note: we check for "True" (case sensitive? usually standardizes to True/False in helpers)
    # pd_helpers uses string interpolation which uses python bool str: "True" / "False"
    current_ratio_pass = "True" in current_ratio_raw
    operating_margin_pass = "True" in operating_margin_raw
    profit_margin_pass = "True" in profit_margin_raw
    roe_pass = "True" in roe_raw
    # net_income_pass already set
    # capital_vs_debt_pass already set
    
    # Apply formatting using captured booleans and raw strings
    current_ratio_check = format_valid(current_ratio_pass, current_ratio_raw)
    net_income_check = format_valid(net_income_pass, net_income_raw)
    operating_margin_check = format_valid(operating_margin_pass, operating_margin_raw)
    profit_margin_check = format_valid(profit_margin_pass, profit_margin_raw)
    roe_check = format_valid(roe_pass, roe_raw)
    capital_vs_debt_msg = format_valid(capital_vs_debt_pass, capital_vs_debt_raw)

    # Calculate overall status using valid booleans
    all_passed = all([
        current_ratio_pass,
        net_income_pass,
        operating_margin_pass,
        profit_margin_pass,
        roe_pass,
        capital_vs_debt_pass
    ])
    
    report_str = f"""
\n\n> **Basic Reports Check**
- current ratio (≥ {current_ratio_min}): {current_ratio_check}
- net income (Positive Trend):  {net_income_check}
- operating margin (avg ≥ {operating_margin_min_avg}%):  {operating_margin_check}
- profit margin (avg ≥ {profit_margin_min_avg}%):  {profit_margin_check}
- working capital vs long-term debt (WC ≥ debt):  {capital_vs_debt_msg}
- ROE (avg ≥ {roe_min_avg}%):  {roe_check}
    """
    return report_str, all_passed
