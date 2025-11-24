import asyncio
import json
from datetime import datetime
from playwright.async_api import Page
from playwright_utils.close_popup import close_popup
from utils.file_handler import load_json_file, append_to_markdown_file
from config import EXISTING_STOCKS_FILE_PATH, NEW_COMPANIES_FILE_PATH



async def load_filtered_companies(page: Page, update_list: bool = False) -> dict:
    companies_dict = load_json_file(EXISTING_STOCKS_FILE_PATH)
    # update_filtered_stocks = False
    if update_list or not companies_dict:
        companies_dict = await get_filtered_companies_from_screener(page)
    return companies_dict

async def get_filtered_companies_from_screener(page: Page) -> dict:
    """Navigate and wait for button, handling popups."""
    # Navigate to URL
    await page.goto("https://stockanalysis.com/stocks/screener/")

    # Load existing companies to track new ones
    existing_companies = load_json_file(EXISTING_STOCKS_FILE_PATH) or {}

    dict_of_companies = {}
    new_companies = []

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
                dict_of_companies[symbol] = {'symbol': symbol, 'href': href, 'sector': sector}

                # Track new companies
                if symbol not in existing_companies:
                    new_companies.append({'symbol': symbol, 'href': href, 'sector': sector})
            
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

                # Save the full companies dictionary to JSON
                with open(EXISTING_STOCKS_FILE_PATH, "w") as f:
                    json.dump(dict_of_companies, f, indent=2)

                # Append new companies to markdown file if any found
                if new_companies:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    md_content = f"\n## {timestamp}\n"
                    for company in new_companies:
                        md_content += f"- **{company['symbol']}** | {company['sector']} | {company['href']}\n"
                    append_to_markdown_file(NEW_COMPANIES_FILE_PATH, md_content)
                    print(f"Added {len(new_companies)} new companies to {NEW_COMPANIES_FILE_PATH}")

                return dict_of_companies
        except Exception as e:
            print(f"Waiting for button: {e}")
            await asyncio.sleep(0.5)