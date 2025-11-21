import pandas as pd
from enum import Enum
from .logger import get_logger

logger = get_logger()


def check_missing_rows_in_df(df, required_rows: list, df_name: str = None) -> list:
    "required rows is a list of enum members"
    missing_rows = [row for row in required_rows if row not in df.index]
    if missing_rows:
        t = f"for {df_name}" if df_name else ""
        logger.warning(f"missing_rows {t}: {missing_rows}")
        return missing_rows
    return []



def check_row_data(df: pd.DataFrame, row_index: Enum, years_cols: list, min_avg=0, min_sum=0):
    cols = years_cols if years_cols else df.columns
    try:
        row = df.loc[row_index.value, cols]
        # Calculate sum, average (mean), and median
        total = row.sum()
        avg = row.mean()  # mean() is the same as average
        if total >= min_sum and avg >= min_avg:
            pass_check = True
        else:
            pass_check =  False
        return f"**valid?** {pass_check}, avarage: {avg:.2f}, total: {total:.2f}"
    except Exception as e:
        logger.error(e)
        
def check_cell_data(df: pd.DataFrame, row_index: Enum, col, greater_than: float= None, lower_than: float = None):
    cell = df.loc[row_index.value, col]
    cell_valid = True
    greater_than_txt = ""
    if greater_than:
        cell_valid = greater_than <= cell
        greater_than_txt = f"value greater than {greater_than:.2f}. "
    lower_than_txt = ""
    if lower_than:
        cell_valid = lower_than >= cell and cell_valid
        lower_than_txt = f"value lower than {greater_than:.2f}. "

    return f"**valid?**: {cell_valid}, {row_index.value} value ({cell}). {greater_than_txt+lower_than_txt}"


def check_cell_range(df: pd.DataFrame, row_index: Enum, col, min_value: float, max_value: float) -> tuple[bool, str]:
    """Check if a cell value is within a specified range (min < value < max)"""
    try:
        cell = df.loc[row_index.value, col]
        cell_valid = min_value < cell < max_value
        return cell_valid, f"**valid?**: {cell_valid}, {row_index.value} value ({cell:.2f}) should be between {min_value} and {max_value}"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error checking {row_index.value}: {str(e)}"


def check_eps_growth(df: pd.DataFrame, row_index: Enum, years_cols: list, min_growth_percent: float = 30) -> tuple[bool, str]:
    """
    Check EPS growth by comparing average of first 2 years vs last 2 years
    Returns True if growth >= min_growth_percent
    """
    try:
        if len(years_cols) < 5:
            return False, f"**valid?**: False, need at least 5 years of data, got {len(years_cols)}"

        row = df.loc[row_index.value, years_cols]

        # First 2 years (oldest)
        first_two_avg = row.iloc[-2:].mean()  # Last 2 indices are oldest years
        # Last 2 years (most recent)
        last_two_avg = row.iloc[:2].mean()  # First 2 indices are most recent

        if first_two_avg == 0:
            return False, f"**valid?**: False, first period average is 0, cannot calculate growth"

        growth_percent = ((last_two_avg - first_two_avg) / first_two_avg) * 100
        is_valid = growth_percent >= min_growth_percent

        return is_valid, f"**valid?**: {is_valid}, EPS growth: {growth_percent:.2f}% (first 2yr avg: {first_two_avg:.2f}, last 2yr avg: {last_two_avg:.2f})"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error: {str(e)}"


def check_pe_pb_product(ratios_df: pd.DataFrame, pe_index: Enum, pb_index: Enum, col, max_product: float = 22) -> tuple[bool, str]:
    """Check if P/E × P/B < max_product (default 22 for Graham number)"""
    try:
        pe = ratios_df.loc[pe_index.value, col]
        pb = ratios_df.loc[pb_index.value, col]
        product = pe * pb
        is_valid = product < max_product

        return is_valid, f"**valid?**: {is_valid}, P/E × P/B = {pe:.2f} × {pb:.2f} = {product:.2f} (should be < {max_product})"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error: {str(e)}"


def check_p_ocf_vs_pe(ratios_df: pd.DataFrame, p_ocf_index: Enum, pe_index: Enum, col) -> tuple[bool, str]:
    """Check if P/OCF < P/E (for tech companies)"""
    try:
        p_ocf = ratios_df.loc[p_ocf_index.value, col]
        pe = ratios_df.loc[pe_index.value, col]
        is_valid = p_ocf < pe

        return is_valid, f"**valid?**: {is_valid}, P/OCF ({p_ocf:.2f}) < P/E ({pe:.2f})"
    except Exception as e:
        logger.error(e)
        return False, f"**valid?**: False, error: {str(e)}"

