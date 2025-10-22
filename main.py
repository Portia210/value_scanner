import asyncio
import importlib
import sys
import json
from pathlib import Path

from playwright.async_api import (
    ElementHandle,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

# Remove utils from cache to force full reload
for module in list(sys.modules.keys()):
    if module.startswith('utils'):
        del sys.modules[module]

# Now import fresh
from playwright_utils import (
    BrowserManager,
    PageHelper,
    quick_screenshot,
    extract_page_data,
    parse_cookie_string,
    load_cookies_from_file,
)

from close_popup import close_popup
from stock_finantial_filters import stock_finantial_filters

EXISTING_STOCKS_FILE_NAME = "filtered_stocks_1.json"

FINANTIAL_ROUTES = {
    "income-statement": "/financials/",
    "balance-sheet": "/financials/balance-sheet/",
    "cash-flow": "/financials/cash-flow-statement/",
}



async def get_1_filter_stocks_names(page: Page):
    """Navigate and wait for button, handling popups."""
    # Navigate to URL
    await page.goto("https://stockanalysis.com/stocks/screener/")
    list_of_stocks = []
    while True:
        await close_popup(page)

        # Wait for the Next button (specifically with text "Next")
        try:
            # Target table rows within the main table body
            rows_locator = page.locator('#main-table tbody tr')
            rows = await rows_locator.all()
            # Extract text and href from each row
            for row in rows:
                # Symbol and href from first cell (td.sym a)
                symbol_elem = row.locator('td.sym a')
                symbol = await symbol_elem.text_content()
                href = await symbol_elem.get_attribute('href')
                # Sector from the 6th cell (td with sector class)
                sector_elem = row.locator('td.sl').last  # Last td.sl should be sector
                sector = await sector_elem.text_content()
                list_of_stocks.append({'symbol': symbol, 'href': href, 'sector': sector})
            
            button = page.locator('button.controls-btn:has-text("Next")')
            await button.wait_for(state="visible", timeout=5000)

            # Check if button is enabled before clicking
            if not await button.is_disabled():
                print("Next button is enabled and ready - clicking...")
                await button.click()
                # Wait a bit for page to load
                await asyncio.sleep(1)
            else:
                print("Button is disabled, breaking...")
                with open(EXISTING_STOCKS_FILE_NAME, "w") as f:
                    json.dump(list_of_stocks, f, indent=2)
                break
        except Exception as e:
            print(f"Waiting for button: {e}")
            await asyncio.sleep(0.5)
            
def load_existing_stocks(file_path: str):
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print("No existing stocks file found.")
        return None






async def main():
    # Advanced interactions example
    async with BrowserManager(headless=True, slow_mo=100) as manager:
        async with manager.new_context() as context:
            # Load cookies into the context
            cookies = load_cookies_from_file("cookies.txt", domain="stockanalysis.com")
            await context.add_cookies(cookies)

            # Create a page for the initial filtering
            page = await context.new_page()

            existing_stocks = load_existing_stocks(EXISTING_STOCKS_FILE_NAME)
            update_filtered_stocks = True if not existing_stocks  else False
            # update_filtered_stocks = False
            if update_filtered_stocks:
                await get_1_filter_stocks_names(page)
                existing_stocks = load_existing_stocks(EXISTING_STOCKS_FILE_NAME)
                if not existing_stocks:
                    print("No stocks found after filtering. Exiting.")
                    await page.close()
                    return

            # Pass context to stock2filter instead of page
            for stock in existing_stocks:
                await stock_finantial_filters(context, stock['symbol'], stock['href'])

            # Clean up the initial page
            await page.close()
            

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Exiting cleanly.")
        exit(0)