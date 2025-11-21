import pandas as pd
from enums import IncomeIndex, RatiosIndex, BalanceSheetIndex
from utils.pd_helpers import (
    check_cell_data,
    check_missing_rows_in_df,
    check_row_data,
    check_cell_range,
    check_eps_growth,
    check_pe_pb_product,
    check_p_ocf_vs_pe
)
from utils.formatting import format_valid

def benjamin_graham_check(symbol: str, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list, company_sector: str = None):

    """
    Benjamin Graham Investment Criteria Check

    Requirements:
    1. Market Cap > $2B
    2. Revenue > $350M
    3. Working Capital - Long-term Debt > 0
    4. P/E ratio checks (with tech company adjustments)
    5. 30% EPS growth over 5 years

    Note: Current Ratio check is handled in basic_reports_check
    """

    # Determine if this is a tech company
    is_tech_company = False
    if company_sector:
        tech_keywords = ['Technology', 'Software', 'Internet', 'Semiconductor', 'Computer', 'Tech']
        is_tech_company = any(keyword.lower() in company_sector.lower() for keyword in tech_keywords)

    most_recent_year = last_5_years_cols[0]
    company_type = "Tech" if is_tech_company else "Regular"

    # 1. Market Cap > $2B
    try:
        market_cap = ratios_df.loc[RatiosIndex.MARKET_CAPITALIZATION.value, most_recent_year]
        market_cap_check = market_cap > 2000
        market_cap_msg = format_valid(market_cap_check, f"**valid?**: {market_cap_check}, Market Cap: ${market_cap:.2f}M (should be > $2,000M)")
    except Exception as e:
        market_cap_msg = format_valid(False, f"**valid?**: False, error checking market cap: {str(e)}")

    # 2. Revenue > $350M
    try:
        revenue = income_df.loc[IncomeIndex.REVENUE.value, most_recent_year]
        revenue_check = revenue > 350
        revenue_msg = format_valid(revenue_check, f"**valid?**: {revenue_check}, Revenue: ${revenue:.2f}M (should be > $350M)")
    except Exception as e:
        revenue_msg = format_valid(False, f"**valid?**: False, error checking revenue: {str(e)}")

    # 3. Working Capital > Long-term Debt
    if check_missing_rows_in_df(balance_df, [BalanceSheetIndex.LONG_TERM_DEBT.value], "balance df"):
        working_capital = balance_df.loc[BalanceSheetIndex.WORKING_CAPITAL.value, most_recent_year]
        long_term_debt = balance_df.loc[BalanceSheetIndex.LONG_TERM_DEBT.value, most_recent_year]
        wc_greater_debt = working_capital > long_term_debt
        capital_vs_debt_msg = format_valid(wc_greater_debt, f"**valid?**: {wc_greater_debt}, Working Capital - Debt = ${working_capital:.2f}M - ${long_term_debt:.2f}M = ${(working_capital - long_term_debt):.2f}M")
    else:
        capital_vs_debt_msg = format_valid(True, f"**valid?**: True, No long-term debt")

    # 4. P/E Ratio Checks
    pe_min = 5
    pe_max = 25 if is_tech_company else 15
    pe_valid, pe_range_msg = check_cell_range(ratios_df, RatiosIndex.PE_RATIO, most_recent_year, pe_min, pe_max)
    pe_range_msg = format_valid(pe_valid, pe_range_msg)

    # Graham Number: P/E × P/B < 22 (only for non-tech companies)
    if not is_tech_company:
        pe_pb_valid, graham_number_msg = check_pe_pb_product(ratios_df, RatiosIndex.PE_RATIO, RatiosIndex.PB_RATIO, most_recent_year)
        graham_number_msg = format_valid(pe_pb_valid, graham_number_msg)
    else:
        graham_number_msg = "N/A (Tech company - uses P/OCF check instead)"

    # Tech P/OCF check: P/OCF < P/E (only for tech companies if P/E is valid)
    if is_tech_company and pe_valid:
        p_ocf_valid, p_ocf_msg = check_p_ocf_vs_pe(ratios_df, RatiosIndex.P_OCF_RATIO, RatiosIndex.PE_RATIO, most_recent_year)
        p_ocf_msg = format_valid(p_ocf_valid, p_ocf_msg)
    elif is_tech_company:
        p_ocf_msg = "Skipped (P/E invalid)"
    else:
        p_ocf_msg = "N/A (Regular company - uses Graham Number instead)"

    # 5. EPS Growth
    eps_valid, eps_growth_msg = check_eps_growth(income_df, IncomeIndex.EPS_DILUTED, last_5_years_cols, min_growth_percent=30)
    eps_growth_msg = format_valid(eps_valid, eps_growth_msg)

    return f"""
\n\n> **Benjamin Graham Check** ({symbol} - {company_sector or 'Unknown'} - {company_type})
- market cap (> $2B): {market_cap_msg}
- revenue (> $350M): {revenue_msg}
- working capital vs debt (WC > debt): {capital_vs_debt_msg}
- P/E ratio (5-{pe_max}): {pe_range_msg}
- graham number (P/E × P/B < 22): {graham_number_msg}
- tech P/OCF check (P/OCF < P/E): {p_ocf_msg}
- EPS growth (30% over 5yr): {eps_growth_msg}
    """
