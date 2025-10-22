import pandas as pd
import numpy as np


def parse_percentage(percentage_str):
    """Convert percentage string to float (e.g., '25.97%' -> 25.97)"""
    if pd.isna(percentage_str) or percentage_str == '-':
        return np.nan
    return float(str(percentage_str).replace('%', ''))

def parse_row_percentages(row_name, df: pd.DataFrame):
    """Extract percentage values from a specified row in the DataFrame"""
    # Find the row
    row = df[df['Fiscal Year'] == row_name].iloc[0]

    # Dynamically find year columns (exclude 'Fiscal Year' and 'TTM')
    year_columns = [col for col in df.columns if col.startswith('FY ')]
    year_columns.sort()  # Sort chronologically

    values = [parse_percentage(row[col]) for col in year_columns]
    # return row values as pandas Series
    return pd.Series(values, index=year_columns)