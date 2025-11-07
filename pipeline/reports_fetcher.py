import os
import asyncio
from playwright.async_api import Page, BrowserContext
from playwright_utils.page_helper import PageHelper
from playwright.async_api import TimeoutError
from playwright_utils.close_popup import close_popup
import pandas as pd
from io import StringIO
from utils.df_cleaner import full_df_cleaning
from utils.logger import get_logger

logger = get_logger()


REPORTS_ROUTES = {
    "income": "/financials/",
    "balance-sheet": "/financials/balance-sheet/",
    "cash-flow": "/financials/cash-flow-statement/",
    "ratios": "/financials/ratios/",
}

async def extract_html_table_to_df(page: Page, table_selector: str):
    # Get table HTML
    table_html = await page.locator(table_selector).inner_html(timeout=3000)
        
    # Parse with pandas using StringIO
    df = pd.read_html(StringIO(f"<table>{table_html}</table>"))[0]
    # Flatten multi-level columns if any
    df.columns = df.columns.get_level_values(0)
    # Remove columns where any cell contains "Upgrade"
    for col in df.columns:
        if (df[col] == 'Upgrade').any():
            df = df.drop(columns=[col])
    return df


class ReportsFetcher:
    def __init__(self, context: BrowserContext, ticker: str, href: str):
        self.context = context
        self.ticker = ticker
        self.href = href
        
    
    def is_report_exists(self, report_type: str) -> bool:
        file_path = f"data/{self.ticker}/{report_type}.csv"
        return os.path.exists(file_path)

    async def _fetch_report(self, report_type: str):
        
        if self.is_report_exists(report_type):
            return
        
        # Create a new page for this report
        page = await self.context.new_page()
        helper = PageHelper(page)

        try:
            
            for _ in range(3):  # Retry up to 3 times
                try:
                    await helper.navigate(f"https://stockanalysis.com{self.href}{REPORTS_ROUTES[report_type]}")
                    await close_popup(page)
                    df = await extract_html_table_to_df(page, "table.financials-table")
                    break  # Exit retry loop on success
                except TimeoutError:
                    logger.warning(f"Timeout while trying to get table HTML, sleeping and retrying...")
                    await asyncio.sleep(5)
            
            # convert all the df to clean floats
            df = full_df_cleaning(df)
            # Save to data directory
            os.makedirs("data", exist_ok=True)
            os.makedirs(f"data/{self.ticker}", exist_ok=True)
            df.to_csv(f"data/{self.ticker}/{report_type}.csv")
            return df
        finally:
            # Always close the page after extraction
            await page.close()
            
    def is_report_missing(self) -> bool:
        if not os.path.exists(f"data/{self.ticker}"):
            return True
        wanted_reports = REPORTS_ROUTES.keys()
        exsisting_reports_in_folder = os.listdir(os.path.join("data", self.ticker)) 
        
        missing_reports = []
        for i, report in enumerate(wanted_reports):
            if report + ".csv" not in exsisting_reports_in_folder:
                missing_reports.append(report)
                
        if missing_reports:
            logger.info(f"Reports missing for {self.ticker}: {missing_reports}")
            return True
        logger.info(f"All reports exist for {self.ticker}.")
        return False
    
    async def fetch_all_reports(self):
        if not self.is_report_missing():
            return
        
        tasks = [self._fetch_report(report_type) for report_type in REPORTS_ROUTES.keys()]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)  # brief pause to ensure all file operations complete