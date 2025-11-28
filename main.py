import asyncio
import json
from pathlib import Path

# Now import fresh
from playwright_utils import BrowserManager, load_cookies_from_file
from pipeline.reports_fetcher import ReportsFetcher
from pipeline.get_filtered_companies import load_filtered_companies
from pipeline.report_maker import generate_report
from utils.logger import get_logger

logger = get_logger()


FINANTIAL_ROUTES = {
    "income-statement": "/financials/",
    "balance-sheet": "/financials/balance-sheet/",
    "cash-flow": "/financials/cash-flow-statement/",
}


            


async def main():
    # Advanced interactions example
    async with BrowserManager(headless=True, slow_mo=100) as manager:
        async with manager.new_context() as context:
            # Load cookies into the context
            cookies = load_cookies_from_file("cookies.txt", domain="stockanalysis.com")
            await context.add_cookies(cookies)
            page = await context.new_page()
            
            update_list = True if input("do you want to update stock symbols? type y or any other key: ") == "y" else False

            companies_dict = await load_filtered_companies(page, update_list)
            if not companies_dict:
                logger.info("No stocks found after filtering. Exiting.")
                await page.close()
                return
            
            return

            
            # Pass context to stock2filter instead of page
            for symbol, company_info in companies_dict.items():
                try:
                    fetcher = ReportsFetcher(context, company_info['symbol'], company_info['href'])
                    # await fetcher.fetch_all_reports()
                    generate_report(symbol)
                except Exception as e:
                    logger.info(f"Error processing stock {company_info['symbol']}: {e}")
            # Clean up the initial page
            await page.close()
            

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nProgram interrupted by user. Exiting cleanly.")
        exit(0)