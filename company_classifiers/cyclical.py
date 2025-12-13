from constants.sectors import CYCLICAL_SECTORS, CYCLICAL_INDUSTRIES

def is_cyclical_sector_or_industry(sector: str, industry: str) -> bool:
    """Check if sector or industry is cyclical."""
    return (sector in CYCLICAL_SECTORS) or (industry in CYCLICAL_INDUSTRIES)

def is_volatile(volatility: float, threshold: float = 0.40) -> bool:
    """Check if earnings volatility is high."""
    return volatility > threshold

def is_high_beta(beta: float, threshold: float = 1.5) -> bool:
    """Check if beta is high."""
    return beta is not None and beta > threshold

def is_cyclical(sector: str, industry: str, volatility: float, beta: float) -> tuple[bool, list[str]]:
    """
    Check if company matches any cyclical criteria.
    Returns (is_cyclical, reasons).
    """
    reasons = []
    
    if is_cyclical_sector_or_industry(sector, industry):
        if sector in CYCLICAL_SECTORS:
            reasons.append(f"Sector: {sector}")
        if industry in CYCLICAL_INDUSTRIES:
            reasons.append(f"Industry: {industry}")
            
    if is_volatile(volatility):
        reasons.append(f"High Volatility (CV: {volatility:.2f})")
        
    if is_high_beta(beta):
        reasons.append(f"High Beta ({beta:.2f})")
        
    return len(reasons) > 0, reasons
