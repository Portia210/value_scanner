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


def check_eps_growth(df: pd.DataFrame, row_index: Enum, years_cols: list, min_growth_percent: float = 30) -> tuple[bool, str]:
    """Check EPS growth: average of first 2 years vs last 2 years."""
    if len(years_cols) < 5:
        return False, f"**valid?**: False, need at least 5 years of data, got {len(years_cols)}"

    row = get_row_safe(df, row_index, years_cols)
    if row is None:
        return False, f"**valid?**: False, row '{row_index.value}' not found in data"

    try:
        # First 2 years (oldest)
        first_two_avg = row.iloc[-2:].mean()
        # Last 2 years (most recent)
        last_two_avg = row.iloc[:2].mean()

        if first_two_avg == 0:
            return False, f"**valid?**: False, first period average is 0, cannot calculate growth"

        growth_percent = ((last_two_avg - first_two_avg) / first_two_avg) * 100
        is_valid = growth_percent >= min_growth_percent

        return is_valid, f"**valid?**: {is_valid}, EPS growth: {growth_percent:.2f}% (first 2yr avg: {first_two_avg:.2f}, last 2yr avg: {last_two_avg:.2f})"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error calculating growth: {str(e)}"


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
