import os
from .logger import get_logger
from enum import Enum
from config import CsvFiles

logger = get_logger()




def get_symbol_csvs_paths(ticker) -> dict:
    folder_path = os.path.join('data', ticker)
    if not os.path.exists(folder_path):
        logger.error(f"Folder path does not exist: {folder_path}")
        return None
    paths = {}
    for csv_member in CsvFiles:
        paths[csv_member.value] = os.path.join(folder_path, f"{csv_member.value}.csv")
    return paths


if __name__ == "__main__":
    logger.info(get_symbol_csvs_paths("YETI"))