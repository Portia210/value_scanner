from playwright_utils import BrowserManager, load_cookies_from_file
from pipeline.get_filtered_companies import load_filtered_companies
from config import COOKIES_FILE_PATH
from utils.logger import get_logger

logger = get_logger()

async def update_stock_list_interactive(update_list: bool = True) -> dict:
    """
    Launch browser to update stock list if requested.
    Returns the companies dictionary.
    """
    companies_dict = {}
    
    if update_list:
        logger.info("Starting browser to update stock list...")
        async with BrowserManager(headless=False, slow_mo=100) as manager:
            async with manager.new_context() as context:
                # Load cookies into the context
                if COOKIES_FILE_PATH.exists():
                    cookies = load_cookies_from_file(str(COOKIES_FILE_PATH), domain="stockanalysis.com")
                    await context.add_cookies(cookies)
                else:
                    logger.warning(f"Cookies file not found at {COOKIES_FILE_PATH}")
                    
                page = await context.new_page()
                
                companies_dict = await load_filtered_companies(page, update_list)
                if not companies_dict:
                    logger.info("No stocks found after filtering.")
                
                await page.close()
    else:
        # Load directly from file without browser
        from config import EXISTING_STOCKS_FILE_PATH
        from utils.file_handler import load_json_file
        companies_dict = load_json_file(EXISTING_STOCKS_FILE_PATH)
        if not companies_dict:
            logger.info("No stocks loaded from file.")
            
    return companies_dict
