"""Generic pandas DataFrame utilities for safe data access and validation."""

import pandas as pd
from io import StringIO
from playwright.async_api import Page
from enum import Enum
from bs4 import BeautifulSoup
from .logger import get_logger

logger = get_logger()




async def extract_html_table_to_df(page: Page, table_selector: str, href_col_number: int = None):
    """Extract HTML table to DataFrame, optionally extracting href from specific td column."""

    # Get table HTML
    table_html = await page.locator(table_selector).inner_html(timeout=3000)
    return parse_html_table_str(table_html, href_col_number)


def parse_html_table_str(table_html: str, href_col_number: int = None) -> pd.DataFrame:
    """Parse HTML table string to DataFrame."""
    full_table_html = f"<table>{table_html}</table>"

    # Parse table with pandas
    df = pd.read_html(StringIO(full_table_html))[0]
    df.columns = df.columns.get_level_values(0)  # Flatten multi-level columns

    # Extract hrefs if requested
    if href_col_number is not None:
        soup = BeautifulSoup(full_table_html, 'html.parser')
        data_rows = soup.find_all('tr')[1:]  # Skip header row

        hrefs = []
        for row in data_rows[:len(df)]:
            tds = row.find_all('td')
            link = tds[href_col_number].find('a') if href_col_number < len(tds) else None
            hrefs.append(link.get('href') if link else None)

        df['href'] = hrefs

    # Remove columns containing "Upgrade"
    upgrade_cols = [col for col in df.columns if (df[col] == 'Upgrade').any()]
    df = df.drop(columns=upgrade_cols)

    return df

# ============================================================================
# SAFE GETTER FUNCTIONS
# ============================================================================

def get_cell_safe(df: pd.DataFrame, row_index: Enum, col) -> float | None:
    """Get single cell value, returns None if missing/NaN."""
    try:
        if row_index.value not in df.index:
            return None
        value = df.loc[row_index.value, col]
        return None if pd.isna(value) else value
    except Exception as e:
        logger.error(f"Error getting cell {row_index.value}: {e}")
        return None


def get_row_safe(df: pd.DataFrame, row_index: Enum, cols: list = None) -> pd.Series | None:
    """Get entire row, returns None if missing."""
    try:
        if row_index.value not in df.index:
            return None
        columns = cols if cols else df.columns
        return df.loc[row_index.value, columns]
    except Exception as e:
        logger.error(f"Error getting row {row_index.value}: {e}")
        return None


# ============================================================================
# GENERIC VALIDATION FUNCTIONS
# ============================================================================

def find_missing_rows(df, required_rows: list, df_name: str = None) -> list:
    """Check which required rows are missing from DataFrame."""
    missing_rows = [row for row in required_rows if row not in df.index]
    if "Long-Term Debt" in missing_rows:
        missing_rows.remove("Long-Term Debt")
    if missing_rows:
        t = f"for {df_name}" if df_name else ""
        logger.warning(f"missing_rows {t}: {missing_rows}")
        return missing_rows
    return []


def validate_row_thresholds(df: pd.DataFrame, row_index: Enum, years_cols: list, min_avg=0, min_sum=0):
    """Validate row against minimum average and sum thresholds."""
    cols = years_cols if years_cols else df.columns
    row = get_row_safe(df, row_index, cols)

    if row is None:
        return f"**valid?** False, row '{row_index.value}' not found in data"

    try:
        total = row.sum()
        avg = row.mean()
        pass_check = total >= min_sum and avg >= min_avg
        return f"**valid?** {pass_check}, avarage: {avg:.2f}, total: {total:.2f}"
    except Exception as e:
        logger.error(e)
        return f"**valid?** False, error reading '{row_index.value}': {str(e)}"


def validate_cell_bounds(df: pd.DataFrame, row_index: Enum, col, greater_than: float = None, lower_than: float = None):
    """Validate cell value against min/max thresholds."""
    cell = get_cell_safe(df, row_index, col)

    if cell is None:
        return f"**valid?**: False, row '{row_index.value}' not found in data"

    try:
        cell_valid = True
        greater_than_txt = ""
        if greater_than is not None:
            cell_valid = greater_than <= cell
            greater_than_txt = f"value greater than {greater_than:.2f}. "
        lower_than_txt = ""
        if lower_than is not None:
            cell_valid = lower_than >= cell and cell_valid
            lower_than_txt = f"value lower than {lower_than:.2f}. "

        return f"**valid?**: {cell_valid}, {row_index.value} value ({cell}). {greater_than_txt+lower_than_txt}"
    except Exception as e:
        logger.error(e)
        return f"**valid?**: False, error reading '{row_index.value}': {str(e)}"
