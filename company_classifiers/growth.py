def is_high_growth(eps_growth: float, threshold: float = 25.0) -> bool:
    """Check if EPS growth exceeds the threshold."""
    return eps_growth is not None and eps_growth > threshold
