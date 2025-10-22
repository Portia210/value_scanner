"""Quick action utilities for common Playwright tasks."""
from pathlib import Path
from typing import Optional

from .browser_manager import BrowserManager
from .config import BrowserType
from .page_helper import PageHelper


async def quick_screenshot(
    url: str,
    output_path: str | Path,
    browser_type: BrowserType = "chromium",
    headless: bool = True,
    full_page: bool = False,
) -> bool:
    """
    Quickly take a screenshot of a URL.

    Screenshots are automatically saved to the screenshots/ directory
    unless an absolute path is provided.

    Args:
        url: URL to screenshot
        output_path: Path to save screenshot (auto-saved to screenshots/)
        browser_type: Type of browser to use
        headless: Whether to run browser in headless mode
        full_page: Capture full scrollable page

    Returns:
        bool: True if screenshot succeeded, False otherwise
    """
    async with BrowserManager(browser_type=browser_type, headless=headless) as manager:
        async with manager.new_page() as page:
            helper = PageHelper(page)
            if await helper.navigate(url):
                return await helper.screenshot(output_path, full_page=full_page)
    return False


async def extract_page_data(
    url: str,
    selectors: dict[str, str],
    browser_type: BrowserType = "chromium",
    headless: bool = True,
) -> dict[str, Optional[str]]:
    """
    Extract text data from multiple elements on a page.

    Args:
        url: URL to scrape
        selectors: Dictionary mapping keys to CSS selectors
        browser_type: Type of browser to use
        headless: Whether to run browser in headless mode

    Returns:
        dict: Dictionary mapping keys to extracted text content
    """
    results = {}
    async with BrowserManager(browser_type=browser_type, headless=headless) as manager:
        async with manager.new_page() as page:
            helper = PageHelper(page)
            if await helper.navigate(url):
                for key, selector in selectors.items():
                    results[key] = await helper.get_text(selector)
            else:
                results = {key: None for key in selectors}
    return results
