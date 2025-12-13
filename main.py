import asyncio
import os
import shutil
import pandas as pd
from config import DATA_DIR, FILTERS_CSV_PATH
from pipeline.update_stock_list import update_stock_list_interactive
from pipeline.batch_processor import batch_process_companies
from utils.logger import get_logger

logger = get_logger()

def cleanup_stale_data(companies_dict: dict):
    """
    Remove data folders for symbols not in the current companies list.
    """
    if not companies_dict:
        return

    if DATA_DIR.exists():
        valid_symbols = set(companies_dict.keys())
        existing_folders = set(f.name for f in DATA_DIR.iterdir() if f.is_dir())
        
        stale_folders = existing_folders - valid_symbols
        for folder in stale_folders:
            folder_path = DATA_DIR / folder
            try:
                shutil.rmtree(folder_path)
                logger.info(f"Removed stale data folder: {folder}")
            except Exception as e:
                logger.error(f"Error removing {folder}: {e}")

def sort_results_csv():
    """
    Sort the results CSV alphabetically by Symbol.
    """
    try:
        if FILTERS_CSV_PATH.exists():
            logger.info("Sorting filters_results.csv...")
            df_results = pd.read_csv(FILTERS_CSV_PATH)
            # Ensure no duplicates if any
            df_results.drop_duplicates(subset=['Symbol'], keep='last', inplace=True)
            df_results.sort_values(by='Symbol', inplace=True)
            df_results.to_csv(FILTERS_CSV_PATH, index=False)
            logger.info("Sorted filters_results.csv successfully.")
    except Exception as e:
        logger.error(f"Error sorting results CSV: {e}")

async def main():
    # 1. Update Stock List
    # Ask for update first
    user_input = input("do you want to update stock symbols? type y or any other key: ")
    update_list = True if user_input.lower() == "y" else False
    
    companies_dict = await update_stock_list_interactive(update_list)
    
    if not companies_dict:
        logger.warning("No companies found or loaded. Exiting.")
        return

    # 2. Cleanup
    cleanup_stale_data(companies_dict)

    # 3. Batch Process (Fetch & Report)
    await batch_process_companies(companies_dict)
    
    # 4. Final Sorting
    sort_results_csv()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nProgram interrupted by user. Exiting cleanly.")
        exit(0)