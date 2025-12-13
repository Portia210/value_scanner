from constants.sectors import TECH_SECTORS

def is_tech(sector: str) -> bool:
    """Check if the company is in a Technology sector."""
    return sector in TECH_SECTORS
