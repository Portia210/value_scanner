import pandas as pd
from enums import IncomeIndex, RatiosIndex, BalanceSheetIndex
from utils.pd_helpers import get_cell_safe
from utils.formatting import format_valid
from utils.logger import get_logger
from .formula_helpers import (
    check_cell_range,
    check_eps_growth,
    check_graham_number,
    check_p_ocf_vs_pe
)

logger = get_logger()

def benjamin_graham_check(symbol: str, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list, classification_res: dict = None):

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
    # Use Classification Result logic
    company_type = classification_res.get("type", "Defensive")
    valuation_method = classification_res.get("valuation_method", "Graham")
    
    # "Tech Logic" in Graham Check basically means "Growth/Cyclical" logic (P/OCF Check)
    # So if valuation_method is P/OCF, we treat it as "Tech" for the sake of branching
    is_growth_mode = valuation_method == "P/OCF"
    is_tech_company = is_growth_mode # Map to existing variable name to minimize diff, or rename if cleaner. 
    # Let's keep is_tech_company variable name but assign it based on method.
    
    company_sector = classification_res.get("sector", "Unknown") # For legacy usage if any

    most_recent_year = last_5_years_cols[0]
    # company_type is already set from classification_res['type']

    # 1. Market Cap > $2B
    market_cap = get_cell_safe(ratios_df, RatiosIndex.MARKET_CAPITALIZATION, most_recent_year)

    if market_cap is None:
        market_cap_pass = False
        market_cap_raw = "**valid?**: False, Market Cap data not found"
    else:
        market_cap_pass = market_cap > 2000
        market_cap_raw = f"**valid?**: {market_cap_pass}, Market Cap: \\${market_cap:.2f}M (should be > \\$2,000M)"
    
    market_cap_msg = format_valid(market_cap_pass, market_cap_raw)

    # 2. Revenue > $350M
    revenue = get_cell_safe(income_df, IncomeIndex.REVENUE, most_recent_year)

    if revenue is None:
        revenue_pass = False
        revenue_msg_raw = "**valid?**: False, Revenue data not found"
    else:
        revenue_pass = revenue > 350
        revenue_msg_raw = f"**valid?**: {revenue_pass}, Revenue: \\${revenue:.2f}M (should be > \\$350M)"
        
    revenue_msg = format_valid(revenue_pass, revenue_msg_raw)

    # 3. Working Capital > Long-term Debt
    working_capital = get_cell_safe(balance_df, BalanceSheetIndex.WORKING_CAPITAL, most_recent_year)
    long_term_debt = get_cell_safe(balance_df, BalanceSheetIndex.LONG_TERM_DEBT, most_recent_year)

    if long_term_debt is None or long_term_debt == 0:
        wc_greater_debt_pass = True
        capital_vs_debt_raw = "**valid?**: True, No long-term debt"
    elif working_capital is None:
        wc_greater_debt_pass = False
        capital_vs_debt_raw = "**valid?**: False, Working capital data unavailable"
    else:
        wc_greater_debt_pass = working_capital > long_term_debt
        capital_vs_debt_raw = f"**valid?**: {wc_greater_debt_pass}, Working Capital - Debt = ${working_capital:.2f}M - ${long_term_debt:.2f}M = ${(working_capital - long_term_debt):.2f}M"
        
    capital_vs_debt_msg = format_valid(wc_greater_debt_pass, capital_vs_debt_raw)

    # 4. P/E Ratio Checks
    pe_min = 5
    pe_max = 25 if is_tech_company else 15
    pe_pass, pe_range_raw = check_cell_range(ratios_df, RatiosIndex.PE_RATIO, most_recent_year, pe_min, pe_max)
    pe_range_msg = format_valid(pe_pass, pe_range_raw)

    # Graham Number: P/E × P/B < 22 (only for non-tech companies)
    if not is_tech_company:
        pe_pb_pass, graham_number_raw = check_graham_number(ratios_df, RatiosIndex.PE_RATIO, RatiosIndex.PB_RATIO, most_recent_year)
        graham_number_msg = format_valid(pe_pb_pass, graham_number_raw)
    else:
        pe_pb_pass = True # Considered "pass" or N/A for tech? 
        # Actually, if it's N/A, it shouldn't affect the boolean AND logic?
        # The logic below splits the list based on type, so this value shouldn't be used for Tech.
        # But safest to set it to False or N/A logic.
        graham_number_msg = "N/A (Tech company - uses P/OCF check instead)"

    # Tech P/OCF check: P/OCF < P/E (only for tech companies if P/E is valid)
    if is_tech_company:
        p_ocf_pass, p_ocf_raw = check_p_ocf_vs_pe(ratios_df, RatiosIndex.P_OCF_RATIO, RatiosIndex.PE_RATIO, most_recent_year)
        p_ocf_msg = format_valid(p_ocf_pass, p_ocf_raw)
    else:
        p_ocf_pass = True # Unused in non-tech
        p_ocf_msg = "N/A (Regular company - uses Graham Number instead)"

    # 5. EPS Growth
    eps_pass, eps_growth_raw = check_eps_growth(income_df, IncomeIndex.EPS_DILUTED, last_5_years_cols, min_growth_percent=30)
    eps_growth_msg = format_valid(eps_pass, eps_growth_raw)
    
    if is_tech_company:
        # Tech logic
        # Note: pe_pass is included as per requirements
        all_valids = [market_cap_pass, revenue_pass, wc_greater_debt_pass, pe_pass, p_ocf_pass, eps_pass]
    else:
        # Non-Tech logic
        all_valids = [market_cap_pass, revenue_pass, wc_greater_debt_pass, pe_pass, pe_pb_pass, eps_pass]
        
    all_passed = all(all_valids)
    
    report_str = f"""
\n\n> **Benjamin Graham Check** ({symbol} - {company_sector or 'Unknown'} - {company_type})
- market cap (> \\$2B): {market_cap_msg}
- revenue (> \\$350M): {revenue_msg}
- working capital vs debt (WC > debt): {capital_vs_debt_msg}
- P/E ratio (5-{pe_max}): {pe_range_msg}
- graham number (P/E × P/B < 22): {graham_number_msg}
- tech P/OCF check (P/OCF < P/E): {p_ocf_msg}
- EPS growth (30% over 5yr): {eps_growth_msg}
    """
    return report_str, all_passed
