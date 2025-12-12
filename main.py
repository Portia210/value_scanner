import asyncio
import os
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


            



import httpx
from pipeline.http_reports_fetcher import HttpReportsFetcher

async def process_company(semaphore: asyncio.Semaphore, fetcher: HttpReportsFetcher, symbol: str, company_info: dict):
    async with semaphore:
        try:
            report_path = f"data/{symbol}/report.md"
            if os.path.exists(report_path):
                return

            await fetcher.fetch_all_reports(symbol, company_info['href'])
            generate_report(symbol)
        except Exception as e:
            logger.info(f"Error processing stock {symbol}: {e}")

async def main():
    # Ask for update first
    update_list = True if input("do you want to update stock symbols? type y or any other key: ") == "y" else False
    
    companies_dict = {}
    
    if update_list:
        # Advanced interactions example
        async with BrowserManager(headless=False, slow_mo=100) as manager:
            async with manager.new_context() as context:
                # Load cookies into the context
                cookies = load_cookies_from_file("cookies.txt", domain="stockanalysis.com")
                await context.add_cookies(cookies)
                page = await context.new_page()
                
                companies_dict = await load_filtered_companies(page, update_list)
                if not companies_dict:
                    logger.info("No stocks found after filtering. Exiting.")
                    await page.close()
                    return
                await page.close()
    else:
        # Load directly from file without browser
        from config import EXISTING_STOCKS_FILE_PATH
        from utils.file_handler import load_json_file
        companies_dict = load_json_file(EXISTING_STOCKS_FILE_PATH)
        if not companies_dict:
            logger.info("No stocks loaded from file. Run with 'y' to fetch.")
            return

    # HTTP fetching phase
    # Increase concurrency since HTTP is lighter than browser pages
    sem = asyncio.Semaphore(2)  # Reduced to 2 to respect rate limits 
    
    # Create a shared httpx client
    async with httpx.AsyncClient(timeout=30.0) as client:
        http_fetcher = HttpReportsFetcher(client)
        
        tasks = []
        for symbol, company_info in companies_dict.items():
            tasks.append(process_company(sem, http_fetcher, symbol, company_info))
        
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nProgram interrupted by user. Exiting cleanly.")
        exit(0)