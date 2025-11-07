import os
import logging
import pandas as pd
from utils.logger import get_logger


logger = get_logger()

def get_row_by_index(df, name):
    row = df[df.index == name]
    if not row.empty:
        return row.iloc[0]
    return None

def set_df_index_by_column(df, column_name):
    df.set_index(column_name, inplace=True)

def strip_dataframe(dataframe):
    dataframe.columns = dataframe.columns.str.strip()
    for i in dataframe.columns:
        if dataframe[i].dtype == 'object':
            dataframe[i] = dataframe[i].map(str.strip)
            

def convert_row_to_float(srs:pd.Series):
    "convert row to float, return the stripped row as Series"
    try:
        if srs.dtype == 'object':
            if any(isinstance(x, str) and '%' in x for x in srs):
                srs.name = srs.name + " (%)"
            srs = srs.apply(lambda x: float(str(x).replace('%','').replace(',','').replace('$','')) 
                if str(x).strip() not in ['-', ''] else float('nan'))
    except Exception as e:
        logger.error(f"Error converting row {srs.name} to float: {e}")
    return srs

def full_df_cleaning(df:pd.DataFrame):
    strip_dataframe(df)
    set_df_index_by_column(df, 'Fiscal Year')
    for index, row in df.iterrows():
        row = convert_row_to_float(row)
        df.loc[index] = row
        df.rename(index={index: row.name}, inplace=True)
    return df






