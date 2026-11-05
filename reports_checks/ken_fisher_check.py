import pandas as pd
from enums import IncomeIndex, RatiosIndex, BalanceSheetIndex
from utils.pd_helpers import validate_cell_bounds, get_cell_safe, get_row_safe
from utils.formatting import format_valid
from utils.logger import get_logger
from reports_checks.formula_helpers import check_eps_growth

logger = get_logger()

def ken_fisher_check(symbol: str, income_df: pd.DataFrame, balance_df: pd.DataFrame, ratios_df: pd.DataFrame, last_5_years_cols: list, classification_res: dict = None):
    """
    Ken Fisher Super Stocks Strategy Check.
    
    Criteria:
    1. Valuation: P/S < 1.5 (Cyclical/Staples < 0.8, Super < 0.4). Tech/Ind Exceptions.
    2. Profitability: Net Margin > 8% (Tech/Health > 15%).
    3. Growth: 5Y EPS Growth > 15%.
    4. Financial Health: D/E < 0.4, FCF/Share > 0.
    5. Innovation (Tech/Pharma): 5 < Price-to-Research < 15, R&D/Rev > 10%.
    """
    
    most_recent_year = last_5_years_cols[0]
    sector = classification_res.get("sector", "Unknown") if classification_res else "Unknown"
    industry = classification_res.get("industry", "Unknown") if classification_res else "Unknown"
    
    # 1. Valuation Criteria (The "Glitch" Check)
    # General: P/S < 1.5
    # Cyclical & Staples: P/S < 0.8 (Super < 0.4)
    # Tech: P/OCF, P/E
    # Industrials: P/E, Graham Number
    
    ps_ratio = get_cell_safe(ratios_df, RatiosIndex.PS_RATIO, most_recent_year)
    pe_ratio = get_cell_safe(ratios_df, RatiosIndex.PE_RATIO, most_recent_year)
    p_ocf = get_cell_safe(ratios_df, RatiosIndex.P_OCF_RATIO, most_recent_year)
    
    valuation_pass = False
    # Logic Flags derived from Verified Classification
    c_type = classification_res.get("type", "Defensive")
    
    # 1. Tech/Pharma/Growth Logic
    # Covers: Technology, BioTech, Pharma, and upgraded "High Growth" companies
    is_tech_mode = c_type in ["Tech/Pharma", "High Growth"]
    
    # 2. Key Sector Exceptions (Still need raw sector for specific rules like Industrial-only)
    is_industrial = sector == "Industrials"
    is_staples = sector == "Consumer Staples"

    # 3. Cyclical Logic
    # Covers: Materials, Energy, etc. AND any "Volatility Trap"
    is_cyclical_mode = c_type == "Cyclical" 
    
    use_strict_ps = is_staples or is_cyclical_mode
    
    if is_tech_mode:
        # Tech/Growth Exception: Use P/OCF < 25 and P/E < 40 (Fisher Tech defaults implied)
        check_p_ocf = p_ocf < 25 if p_ocf else False
        check_pe = pe_ratio < 40 if pe_ratio else False
        valuation_pass = check_p_ocf and check_pe
        valuation_msg = f"**valid?**: {valuation_pass} (Tech Exception), P/OCF: {p_ocf} (<25), P/E: {pe_ratio} (<40)"
        
    elif is_industrial:
        # Industrials Exception: P/E and Graham
        # P/E < 25 (Fisher Industrial)
        check_pe = pe_ratio < 25 if pe_ratio else False
        
        # Graham Check proxy (Price < Graham Number implies P/E * P/B < 22.5)
        # We'll use P/E * P/B here for simplicity if Graham Number logic isn't directly exposed as value
        pb_ratio = get_cell_safe(ratios_df, RatiosIndex.PB_RATIO, most_recent_year)
        if pe_ratio and pb_ratio:
            graham_val = pe_ratio * pb_ratio
            check_graham = graham_val < 25 # Slightly looser than 22.5 for Fisher context? Or Stick to Graham?
            # User said "Graham Number check". Standard is 22.5.
            check_graham = graham_val < 22.5
            valuation_pass = check_pe or check_graham
            valuation_msg = f"**valid?**: {valuation_pass} (Industrial Exception), P/E: {pe_ratio} (<25) OR Graham (PxB): {graham_val:.1f} (<22.5)"
        else:
            valuation_pass = False
            valuation_msg = f"**valid?**: False, Missing P/E or P/B for Graham Check"
            
    elif use_strict_ps:
        # Strict P/S
        target_ps = 0.8
        super_target_ps = 0.4
        
        if ps_ratio is not None:
            valuation_pass = ps_ratio < target_ps
            is_super = ps_ratio < super_target_ps
            valuation_msg = f"**valid?**: {valuation_pass}, P/S: {ps_ratio} (<{target_ps})" + (" (SUPER STOCK!)" if is_super else "")
        else:
             valuation_pass = False
             valuation_msg = "**valid?**: False, Missing P/S Ratio"
             
    else:
        # General Rule
        target_ps = 1.5
        if ps_ratio is not None:
            valuation_pass = ps_ratio < target_ps
            valuation_msg = f"**valid?**: {valuation_pass}, P/S: {ps_ratio} (<{target_ps})"
        else:
             valuation_pass = False
             valuation_msg = "**valid?**: False, Missing P/S Ratio"

    # 2. Profitability (Margins)
    # Tech/Health > 15%, Others > 8%
    net_margin = get_cell_safe(income_df, IncomeIndex.PROFIT_MARGIN_PERCENT, most_recent_year) # Validated as Net Margin
    
    target_margin = 15.0 if is_tech_mode else 8.0
    
    if net_margin is not None:
        margin_pass = net_margin > target_margin
        margin_msg = f"**valid?**: {margin_pass}, Net Margin: {net_margin}% (>{target_margin}%)"
    else:
        margin_pass = False
        margin_msg = "**valid?**: False, Missing Net Margin"

    # 3. Growth Metrics (EPS Growth 5Y > 15%)
    # Utilizing helper
    eps_growth_pass, eps_growth_raw = check_eps_growth(income_df, IncomeIndex.EPS_DILUTED, last_5_years_cols, min_growth_percent=15)
    # The helper returns a raw string formatted for standard check, let's adapt or reuse
    # The helper string format: "**valid?**: {bool}, ..."
    eps_growth_msg = eps_growth_raw

    # 4. Financial Health
    # D/E < 0.4
    de_ratio = get_cell_safe(ratios_df, RatiosIndex.DEBT_EQUITY_RATIO, most_recent_year)
    if de_ratio is not None:
        de_pass = de_ratio < 0.4
        de_msg = f"**valid?**: {de_pass}, D/E: {de_ratio} (<0.4)"
    else:
        de_pass = False
        # Try calculating manually if missing? Total Debt / Equity
        # For now, strict fail
        de_msg = "**valid?**: False, Missing D/E Ratio"

    # FCF/Share > 0
    fcf_share = get_cell_safe(income_df, IncomeIndex.FREE_CASH_FLOW_PER_SHARE, most_recent_year)
    if fcf_share is not None:
        fcf_pass = fcf_share > 0
        fcf_msg = f"**valid?**: {fcf_pass}, FCF/Share: {fcf_share} (>0)"
    else:
        fcf_pass = False
        fcf_msg = "**valid?**: False, Missing FCF/Share"

    # 5. Innovation Factor
    # Split: Tech/Pharma (P/R&D) vs Others (R&D/Revenue)
    
    rnd_exp = get_cell_safe(income_df, IncomeIndex.RESEARCH_AND_DEVELOPMENT, most_recent_year)
    revenue = get_cell_safe(income_df, IncomeIndex.REVENUE, most_recent_year)
    market_cap = get_cell_safe(ratios_df, RatiosIndex.MARKET_CAPITALIZATION, most_recent_year)
    
    # Get 5Y History for R&D and Revenue for both cases (needed for Trend or Tech calc if we wanted, but mainly for "Others")
    rnd_row = get_row_safe(income_df, IncomeIndex.RESEARCH_AND_DEVELOPMENT, last_5_years_cols)
    rev_row = get_row_safe(income_df, IncomeIndex.REVENUE, last_5_years_cols)

    # Check if R&D data exists at all (Red Flag check)
    has_rnd_data = rnd_row is not None and not rnd_row.dropna().empty and rnd_row.sum() != 0
    
    if not has_rnd_data:
        innovation_pass = True
        innovation_msg = "**valid?**: True, N/A (Missing R&D Data)"
    else:
        if is_tech_mode:
            # Tech/Pharma: P/R&D 5-15
            if rnd_exp and rnd_exp > 0 and market_cap:
                prr = market_cap / rnd_exp
                innovation_pass = 5 <= prr <= 15
                innovation_msg = f"**valid?**: {innovation_pass} (Tech/Pharma), P/R&D: {prr:.1f} (Target 5-15)"
            else:
                # Should have been caught by has_rnd_data but double check specific year
                innovation_pass = False
                innovation_msg = "**valid?**: False (Tech/Pharma), Missing Current R&D or Market Cap"
        else:
            # Others: Avg R&D/Revenue > 10%
            if rev_row is not None:
                # Calculate yearly intensity
                # Handle potential 0 revenue to avoid div by zero
                # We align rnd_row and rev_row
                
                # Make sure we have aligned series
                trends = []
                ratios = []
                
                for col in last_5_years_cols:
                    r_val = get_cell_safe(income_df, IncomeIndex.RESEARCH_AND_DEVELOPMENT, col)
                    rev_val = get_cell_safe(income_df, IncomeIndex.REVENUE, col)
                    
                    if r_val is not None and rev_val is not None and rev_val != 0:
                        ratio = (r_val / rev_val) * 100
                        ratios.append(ratio)
                        trends.append(f"{ratio:.1f}%")
                    else:
                         trends.append("N/A")
                
                if ratios:
                    avg_intensity = sum(ratios) / len(ratios)
                    innovation_pass = avg_intensity > 10.0
                    trend_str = ", ".join(trends)
                    innovation_msg = f"**valid?**: {innovation_pass} (Standard), Avg R&D/Rev: {avg_intensity:.1f}% (>10%), Trend: ({trend_str})"
                else:
                    innovation_pass = False
                    innovation_msg = "**valid?**: False (Standard), Insufficient Data for R&D/Rev Calc"
            else:
                innovation_pass = False
                innovation_msg = "**valid?**: False (Standard), Missing Revenue Data"


    # Overall Result
    # Overall Result
    checks = [valuation_pass, margin_pass, eps_growth_pass, de_pass, fcf_pass, innovation_pass]

    all_passed = all(checks)
    
    report_str = f"""
\n\n> **Ken Fisher Super Stocks Check**
- Valuation (Sector based): {format_valid(valuation_pass, valuation_msg)}
- Net Profit Margin (>{target_margin}%): {format_valid(margin_pass, margin_msg)}
- EPS Growth (5Y > 15%): {format_valid(eps_growth_pass, eps_growth_msg)}
- Debt-to-Equity (< 0.4): {format_valid(de_pass, de_msg)}
- FCF/Share (> 0): {format_valid(fcf_pass, fcf_msg)}
- Innovation Factor: {format_valid(innovation_pass, innovation_msg)}
    """
    
    return report_str, all_passed
