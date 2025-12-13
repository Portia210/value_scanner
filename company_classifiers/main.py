from .tech import is_tech
from .pharma import is_pharma
from .growth import is_high_growth
from .cyclical import is_cyclical_sector_or_industry, is_volatile as check_volatility, is_high_beta
from constants.sectors import DEFENSIVE_SECTORS

def classify_company(sector: str, industry: str, cagr_3yr: float, revenue_cagr_3yr: float, volatility: float, beta: float) -> dict:
    """
    Classify a company using Advanced Logic: 3-Year CAGR, Sector Gravity, and Volatility Traps.
    
    Priority Hierarchy:
    1. Tech/Pharma (The Future) -> Tech/Growth (P/OCF)
    2. Defensive Sectors (Gravity) -> Default Defensive, Upgrade if CAGR > 20% (unless Volatile Trap)
    3. Cyclical Sectors -> Cyclical (P/OCF)
    4. The Rest -> Growth if CAGR > 20% (unless Trap), else Defensive.
    """
    reasons = []
    
    # Tier 1: Tech/Pharma
    is_t = is_tech(sector)
    is_p = is_pharma(industry)
    
    if is_t or is_p:
        classification = "Tech/Pharma"
        if is_t: reasons.append(f"Sector: {sector}")
        if is_p: reasons.append(f"Industry: {industry}")
        return {
            "type": classification,
            "valuation_method": "P/OCF",
            "reasons": reasons
        }

    # Revenue Fallback Logic
    # If EPS CAGR is invalid or meaningless (-100%), use Revenue CAGR
    cagr_to_use = cagr_3yr
    metric_used = "EPS CAGR"
    
    if cagr_to_use is None or cagr_to_use <= -99.0:
        if revenue_cagr_3yr is not None:
            cagr_to_use = revenue_cagr_3yr
            metric_used = "Revenue CAGR"
            reasons.append(f"Using Revenue CAGR (EPS Invalid/Negative)")
        else:
            # Both are invalid
            cagr_to_use = 0.0

    # Helper Logic for Growth/Trap
    is_high_cagr = cagr_to_use > 20.0
    is_volatility_trap = check_volatility(volatility, threshold=0.50)
    
    # Tier 2: Defensive Sectors (Sector Gravity)
    if sector in DEFENSIVE_SECTORS:
        # Insurance/Bank Hard-Lock
        industry_lower = str(industry).lower()
        if "insurance" in industry_lower or "bank" in industry_lower:
            reasons.append(f"Sector: {sector} (Defensive)")
            reasons.append(f"Industry Hard-Lock: {industry} (No Growth Upgrade)")
            return {
                "type": "Defensive",
                "valuation_method": "Graham",
                "reasons": reasons
            }

        if is_high_cagr:
            # Upgrade Exception
            if is_volatility_trap:
                 # Volatility Trap -> Cyclical
                 reasons.append(f"Sector: {sector} (Defensive)")
                 reasons.append(f"{metric_used} > 20% ({cagr_to_use:.1f}%) but High Volatility ({volatility:.2f}) -> Trap")
                 return {
                     "type": "Cyclical",
                     "valuation_method": "P/OCF",
                     "reasons": reasons
                 }
            else:
                 # True High Growth
                 reasons.append(f"Sector: {sector} (Defensive)")
                 reasons.append(f"High Growth Upgrade: {metric_used} > 20% ({cagr_to_use:.1f}%)")
                 return {
                     "type": "High Growth",
                     "valuation_method": "P/OCF",
                     "reasons": reasons
                 }
        else:
            # Default Gravity -> Defensive
            reasons.append(f"Sector: {sector} (Defensive Gravity)")
            return {
                "type": "Defensive",
                "valuation_method": "Graham",
                "reasons": reasons
            }

    # Tier 3: Cyclical Sectors
    if is_cyclical_sector_or_industry(sector, industry):
        reasons.append("Cyclical Sector/Industry")
        return {
             "type": "Cyclical",
             "valuation_method": "P/OCF",
             "reasons": reasons
        }

    # Tier 4: The Rest (Industrials, Consumer Discretionary, etc.)
    
    if is_high_cagr:
        if is_volatility_trap:
            reasons.append(f"High Growth ({cagr_to_use:.1f}%) but High Volatility ({volatility:.2f}) -> Trap")
            return {
                "type": "Cyclical",
                "valuation_method": "P/OCF",
                "reasons": reasons
            }
        else:
            reasons.append(f"High Growth: {metric_used} > 20% ({cagr_to_use:.1f}%)")
            return {
                "type": "High Growth",
                "valuation_method": "P/OCF",
                "reasons": reasons
            }
    
    # Default Fallback
    return {
        "type": "Defensive",
        "valuation_method": "Graham",
        "reasons": ["Standard Value Profile (Low Growth, Non-Cyclical)"]
    }
