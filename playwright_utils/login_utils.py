
import os
from pathlib import Path
from playwright.async_api import Page
from playwright_utils.close_popup import close_popup
from playwright_utils.cookie_utils import save_cookies_from_browser
from utils.logger import get_logger

logger = get_logger()

async def login_and_save_cookies(page: Page, cookie_file_path: str | Path) -> bool:
    """
    Log in to StockAnalysis.com and save cookies.
    
    Args:
        page: Playwright page object
        cookie_file_path: Path to save the cookies
        
    Returns:
        bool: True if successful, False otherwise
    """
    email = os.environ.get("STOCK_ANALYSIS_EMAIL")
    password = os.environ.get("STOCK_ANALYSIS_PASSWORD")
    
    if not email or not password:
        logger.error("STOCK_ANALYSIS_EMAIL or STOCK_ANALYSIS_PASSWORD not found in environment variables.")
        return False
        
    logger.info("Navigating to login page...")
    try:
        await page.goto("https://stockanalysis.com/login/")
        
        # Handle popup if it appears
        await close_popup(page)
        
        logger.info("Filling credentials...")
        await page.fill("input#email", email)
        await page.fill("input#password", password)
        
        # Click login button
        # The user specified: click on button that have in it the text "Log In"
        logger.info("Clicking Log In button...")
        async with page.expect_navigation(timeout=10000):
            await page.click('button:has-text("Log In")')
        
        # Wait a bit for any client-side redirections or cookie setting
        await page.wait_for_load_state("networkidle")
        
        logger.info("Extracting cookies...")
        context = page.context
        cookies = await context.cookies()
        
        if not cookies:
            logger.error("No cookies found after login attempt.")
            return False
            
        save_cookies_from_browser(cookies, cookie_file_path)
        return True
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False
