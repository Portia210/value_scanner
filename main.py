import asyncio
import os
import shutil
import pandas as pd
from dotenv import load_dotenv
from config import DATA_DIR, FILTERS_CSV_PATH, COOKIES_FILE_PATH
from pipeline.update_stock_list import update_stock_list_interactive
from pipeline.batch_processor import batch_process_companies
from company_classifiers.generate_classifications import generate_classification_csv
from playwright_utils import BrowserManager
from playwright_utils.cookie_utils import validate_cookie
from playwright_utils.login_utils import login_and_save_cookies
from utils.logger import get_logger

logger = get_logger()
# Load env vars for possible login
load_dotenv()

async def ensure_valid_cookies():
    """
    Check if cookies are valid. If not, attempt to login and save new ones.
    """
    logger.info(f"Verifying session cookies at {COOKIES_FILE_PATH}...")
    if validate_cookie(COOKIES_FILE_PATH):
        logger.info("Session cookies are valid.")
        return True

    logger.warning("Cookies are invalid, expired, or missing. Initiating auto-login protocol...")
    try:
        async with BrowserManager(headless=False, slow_mo=100) as manager:
            async with manager.new_page() as page:
                success = await login_and_save_cookies(page, COOKIES_FILE_PATH)
                if success:
                    logger.info("Auto-login successful! Session refreshed.")
                    return True
                else:
                    logger.error("Auto-login failed. Please check your credentials in .env.")
                    return False
    except Exception as e:
        logger.error(f"Error during auto-login execution: {e}")
        return False

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

def initialize_output_files():
    """
    Remove existing result files to prevent duplicate entries on rerun.
    """
    logger.info("Cleaning up old result files...")
    
    # Clean CSV
    if FILTERS_CSV_PATH.exists():
        try:
            FILTERS_CSV_PATH.unlink()
            logger.info(f"Removed {FILTERS_CSV_PATH}")
        except Exception as e:
            logger.error(f"Failed to remove {FILTERS_CSV_PATH}: {e}")
            
    # Clean Markdown Dashboard
    from config import OUTPUT_DIR
    md_path = OUTPUT_DIR / "filters_results.md"
    if md_path.exists():
        try:
            md_path.unlink()
            logger.info(f"Removed {md_path}")
        except Exception as e:
            logger.error(f"Failed to remove {md_path}: {e}")

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
    # 0. Ensure Valid Session
    await ensure_valid_cookies()

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

    # 3. Generate Classifications (Source of Truth)
    generate_classification_csv()

    # 4. Clean Output Files
    initialize_output_files()

    # 5. Batch Process (Fetch & Report)
    await batch_process_companies(companies_dict)
    
    # 6. Final Sorting
    sort_results_csv()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nProgram interrupted by user. Exiting cleanly.")
        exit(0)