import asyncio
import json
from datetime import datetime
from playwright.async_api import Page
import pandas as pd
from playwright_utils.close_popup import close_popup
from utils.file_handler import load_json_file, append_to_markdown_file
from config import EXISTING_STOCKS_FILE_PATH, NEW_COMPANIES_FILE_PATH
from utils.pd_helpers import extract_html_table_to_df



async def load_filtered_companies(page: Page, update_list: bool = False) -> dict:
    companies_dict = load_json_file(EXISTING_STOCKS_FILE_PATH)
    # update_filtered_stocks = False
    if update_list or not companies_dict:
        companies_dict = await get_filtered_companies_from_screener(page)
    return companies_dict

async def get_filtered_companies_from_screener(page: Page) -> dict:
    """Navigate and wait for button, handling popups."""
    await page.goto("https://stockanalysis.com/stocks/screener/")

    # Load existing companies for comparison
    existing_companies = load_json_file(EXISTING_STOCKS_FILE_PATH) or {}

    dict_of_companies = {}

    await close_popup(page)
    all_buttons = await page.locator(".my-scrollbar button").all()

    # Click on the filters button
    for button in all_buttons:
        btn_text = await button.text_content()
        if "Filters" in btn_text:
            await button.click()
            break

    while True:
        await close_popup(page)

        try:
            # Extract table with hrefs from first column (symbol column)
            df = await extract_html_table_to_df(page, "#main-table", href_col_number=0)

            # Process each row in the DataFrame
            for idx, row in df.iterrows():
                company_name = row.get('Company Name')  # First column is usually Symbol
                symbol = row.get('Symbol')  # First column is usually Symbol
                href = row.get('href')
                sector = row.get('Sector', '')
                industry = row.get('Industry', '')
                beta = row.get('Beta (5Y)')

                # Create company entry
                company_data = {
                    'company_name': company_name,
                    'symbol': symbol,
                    'href': href,
                    'sector': sector,
                    'industry': industry,
                    'beta': beta
                }

                dict_of_companies[symbol] = company_data
            
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

                # Smart comparison: detect added and removed companies
                old_symbols = set(existing_companies.keys())
                new_symbols = set(dict_of_companies.keys())

                added_symbols = new_symbols - old_symbols
                removed_symbols = old_symbols - new_symbols

                # Only update if changes exist
                if added_symbols or removed_symbols:
                    # Save updated companies to JSON
                    with open(EXISTING_STOCKS_FILE_PATH, "w") as f:
                        json.dump(dict_of_companies, f, indent=2)

                    # Write changes to markdown
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    md_content = f"\n## {timestamp}\n"

                    if added_symbols:
                        md_content += f"\n### Added ({len(added_symbols)})\n"
                        for symbol in sorted(added_symbols):
                            company = dict_of_companies[symbol]
                            md_content += f"- **added** **{symbol}** | {company['sector']} | {company['industry']} | Beta: {company['beta']}\n"

                    if removed_symbols:
                        md_content += f"\n### Removed ({len(removed_symbols)})\n"
                        for symbol in sorted(removed_symbols):
                            company = existing_companies[symbol]
                            md_content += f"- **removed** **{symbol}** | {company.get('sector', '')} | {company.get('industry', '')} | Beta: {company.get('beta', 'N/A')}\n"

                    append_to_markdown_file(NEW_COMPANIES_FILE_PATH, md_content)
                    print(f"Changes detected: {len(added_symbols)} added, {len(removed_symbols)} removed")
                else:
                    print("No changes detected - companies list unchanged")

                return dict_of_companies
        except Exception as e:
            print(f"Waiting for button: {e}")
            await asyncio.sleep(0.5)