import asyncio
import httpx
from pipeline.http_reports_fetcher import HttpReportsFetcher
from pipeline.report_maker import generate_report
from utils.logger import get_logger

logger = get_logger()

async def process_company(semaphore: asyncio.Semaphore, fetcher: HttpReportsFetcher, symbol: str, company_info: dict):
    async with semaphore:
        try:
            # Note: Skip logic is handled inside fetcher or we can add it here if needed
            # For now, we trust the fetcher/generator flow
            await fetcher.fetch_all_reports(symbol, company_info['href'])
            generate_report(symbol)
        except Exception as e:
            logger.info(f"Error processing stock {symbol}: {e}")

async def batch_process_companies(companies_dict: dict):
    """
    Process all companies in the dictionary: fetch reports and generate analysis.
    """
    if not companies_dict:
        logger.warning("No companies to process.")
        return

    # Increase concurrency since HTTP is lighter than browser pages
    # Reduced to 2 to respect rate limits as per previous tuning
    sem = asyncio.Semaphore(2) 
    
    # Create a shared httpx client
    async with httpx.AsyncClient(timeout=30.0) as client:
        http_fetcher = HttpReportsFetcher(client)
        
        tasks = []
        for symbol, company_info in companies_dict.items():
            tasks.append(process_company(sem, http_fetcher, symbol, company_info))
        
        await asyncio.gather(*tasks)
