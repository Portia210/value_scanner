from constants.sectors import PHARMA_INDUSTRIES

def is_pharma(industry: str) -> bool:
    """Check if the company is in a Pharma/Biotech industry."""
    return industry in PHARMA_INDUSTRIES
