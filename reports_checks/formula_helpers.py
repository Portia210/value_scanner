"""Formula-specific helper functions for investment criteria checks."""

import pandas as pd
from enum import Enum
from utils.logger import get_logger
from utils.pd_helpers import get_cell_safe, get_row_safe

logger = get_logger()


def check_cell_range(df: pd.DataFrame, row_index: Enum, col, min_value: float, max_value: float) -> tuple[bool, str]:
    """Check if cell value is within range (min < value < max)."""
    cell = get_cell_safe(df, row_index, col)
    if cell is None:
        return False, f"**valid?**: False, row '{row_index.value}' not found in data"

    try:
        # User requirement: "not smaller than 5" (>=) and "lower than 15" (<)
        # So: min_value <= cell < max_value
        cell_valid = min_value <= cell < max_value
        return cell_valid, f"**valid?**: {cell_valid}, {row_index.value} value ({cell:.2f}) should be between {min_value} (inclusive) and {max_value} (exclusive)"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error reading '{row_index.value}': {str(e)}"


def calculate_eps_growth_percent(df: pd.DataFrame, row_index: Enum, years_cols: list) -> float:
    """Calculate the EPS growth percentage over the period."""
    if len(years_cols) < 5:
        return None

    row = get_row_safe(df, row_index, years_cols)
    if row is None:
        return None

    try:
        # First 2 years (oldest)
        first_two_avg = row.iloc[-2:].mean()
        # Last 2 years (most recent)
        last_two_avg = row.iloc[:2].mean()

        if first_two_avg == 0:
            return None

        growth_percent = ((last_two_avg - first_two_avg) / first_two_avg) * 100
        return growth_percent
    except Exception as e:
        logger.error(e)
        return None


def check_eps_growth(df: pd.DataFrame, row_index: Enum, years_cols: list, min_growth_percent: float = 30) -> tuple[bool, str]:
    """Check EPS growth: average of first 2 years vs last 2 years."""
    growth_percent = calculate_eps_growth_percent(df, row_index, years_cols)
    
    if growth_percent is None:
        # Re-derive error reason for message (simplified for now to avoid redundant logic)
        # Or just check simple conditions again if needed for exact error msg
        if len(years_cols) < 5:
             return False, f"**valid?**: False, need at least 5 years of data, got {len(years_cols)}"
        row = get_row_safe(df, row_index, years_cols)
        if row is None:
             return False, f"**valid?**: False, row '{row_index.value}' not found in data"
        return False, "**valid?**: False, cannot calculate growth (avg is 0 or error)"

    is_valid = growth_percent >= min_growth_percent
    
    # We need to re-fetch avgs just for the message, or return them from calc function. 
    # To keep this clean without changing return signature too much, I'll calculate avgs inline just for display if needed, 
    # or just trust the float.
    # Let's just grab the row again for the message details to ensure 1:1 parity with old message
    row = get_row_safe(df, row_index, years_cols)
    first_two_avg = row.iloc[-2:].mean()
    last_two_avg = row.iloc[:2].mean()

    return is_valid, f"**valid?**: {is_valid}, EPS growth: {growth_percent:.2f}% (first 2yr avg: {first_two_avg:.2f}, last 2yr avg: {last_two_avg:.2f})"


def calculate_earnings_volatility(df: pd.DataFrame, row_index: Enum, years_cols: list) -> float:
    """
    Calculate Coefficient of Variation (CV) for EPS over available years.
    CV = Standard Deviation / Mean
    Returns: Float CV value, or 0.0 if not calculable.
    """
    if len(years_cols) < 2:
        return 0.0

    row = get_row_safe(df, row_index, years_cols)
    if row is None:
        return 0.0
    
    try:
        # Convert to float and drop NaNs
        values = pd.to_numeric(row, errors='coerce').dropna()
        if len(values) < 2:
            return 0.0
            
        mean = values.mean()
        if mean == 0:
            return 0.0 # Avoid division by zero
            
        std = values.std()
        cv = abs(std / mean)
        return cv
    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        return 0.0


def calculate_cagr(df: pd.DataFrame, row_index: Enum, years_cols: list, years: int = 3) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR) over n years.
    Formula: (End / Start)^(1/n) - 1
    
    Args:
        years_cols: List of year columns sorted descending (e.g., ['2024', '2023', ...])
        years: Number of years to look back (default 3 means End vs End-3).
    
    Returns:
        float: CAGR percent (e.g., 25.5 for 25.5%), or None if invalid.
    """
    if len(years_cols) <= years:
        return None

    try:
        # years_cols is sorted desc (Newest first).
        # End Value = years_cols[0]
        # Start Value = years_cols[years]
        
        end_col = years_cols[0]
        start_col = years_cols[years]
        
        end_val = get_cell_safe(df, row_index, end_col)
        start_val = get_cell_safe(df, row_index, start_col)
        
        if end_val is None or start_val is None:
            return None
            
        # CAGR is undefined if start value is negative or zero
        if start_val <= 0:
            return None
            
        # Determine sign of end value to handle direction? 
        # Standard CAGR formula supports positive start only. 
        # If end is negative, it's a -100% loss situation effectively or calculable if real numbers.
        # But if start is positive and end is negative, standard formula (neg/pos)^(1/n) fails for real roots.
        if end_val <= 0:
             # Massive decline
             return -100.0

        cagr = ( (end_val / start_val) ** (1/years) ) - 1
        return cagr * 100.0

    except Exception as e:
        logger.error(f"Error calculating CAGR: {e}")
        return None


def check_graham_number(ratios_df: pd.DataFrame, pe_index: Enum, pb_index: Enum, col, max_product: float = 22) -> tuple[bool, str]:
    """Check Graham Number: P/E × P/B < 22."""
    pe = get_cell_safe(ratios_df, pe_index, col)
    pb = get_cell_safe(ratios_df, pb_index, col)

    if pe is None or pb is None:
        missing = "P/E" if pe is None else "P/B"
        return False, f"**valid?**: False, {missing} ratio not found in data"

    try:
        product = pe * pb
        is_valid = product < max_product
        return is_valid, f"**valid?**: {is_valid}, P/E × P/B = {pe:.2f} × {pb:.2f} = {product:.2f} (should be < {max_product})"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error calculating product: {str(e)}"


def check_p_ocf_vs_pe(ratios_df: pd.DataFrame, p_ocf_index: Enum, pe_index: Enum, col) -> tuple[bool, str]:
    """Check tech company valuation: P/OCF < P/E."""
    p_ocf = get_cell_safe(ratios_df, p_ocf_index, col)
    pe = get_cell_safe(ratios_df, pe_index, col)

    if p_ocf is None or pe is None:
        missing = "P/OCF" if p_ocf is None else "P/E"
        return False, f"**valid?**: False, {missing} ratio not found in data"

    try:
        is_valid = p_ocf < pe
        return is_valid, f"**valid?**: {is_valid}, P/OCF ({p_ocf:.2f}) < P/E ({pe:.2f})"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error comparing ratios: {str(e)}"
