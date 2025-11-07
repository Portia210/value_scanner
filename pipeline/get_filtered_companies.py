import asyncio
import json
from playwright.async_api import Page
from playwright_utils.close_popup import close_popup


EXISTING_STOCKS_FILE_NAME = "filtered_companies.json"

def load_file(file_path: str):
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print("No existing stocks file found.")
        return None



async def load_filtered_companies(page: Page, update_list: bool = False) -> list:
    companies_list = load_file(EXISTING_STOCKS_FILE_NAME)
    # update_filtered_stocks = False
    if update_list or not companies_list:
        companies_list = await get_filtered_companies_from_screener(page)
    return companies_list

async def get_filtered_companies_from_screener(page: Page):
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
                return list_of_stocks
        except Exception as e:
            print(f"Waiting for button: {e}")
            await asyncio.sleep(0.5)