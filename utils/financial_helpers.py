"""Helper functions for financial data processing"""
import pandas as pd


def safe_get_numeric_value(df: pd.DataFrame, row_name: str, column_name: str) -> float:
    """Safely get numeric value from dataframe row"""
    matching_rows = df[df.iloc[:, 0] == row_name]
    if matching_rows.empty:
        print(f"Warning: {row_name} not found in dataframe")
        return 0.0
    try:
        value = matching_rows.iloc[0][column_name]
        return float(str(value).replace(',', ''))
    except (ValueError, IndexError, KeyError) as e:
        print(f"Error processing {row_name}: {e}")
        return 0.0


def add_analysis_rows_to_markdown(md_content: str, rows: list) -> str:
    """Add analysis rows to markdown content"""
    for line in rows:
        md_content += f"{line}\n"
    return md_content