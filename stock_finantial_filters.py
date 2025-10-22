import os
import asyncio
from playwright.async_api import Page, BrowserContext
from playwright_utils.page_helper import PageHelper

from close_popup import close_popup
import pandas as pd
from io import StringIO
from linear_regression import get_row_consistency
from utils.pd_parser import parse_row_percentages
from utils.financial_helpers import safe_get_numeric_value

FINANCIAL_ROUTES = {
    "income": "/financials/",
    "balance-sheet": "/financials/balance-sheet/",
    "cash-flow": "/financials/cash-flow-statement/",
    "ratios": "/financials/ratios/",
}

async def extract_table_to_csv(page: Page, table_selector: str):
    # Get table HTML
    table_html = await page.locator(table_selector).inner_html()

    # Parse with pandas using StringIO
    df = pd.read_html(StringIO(f"<table>{table_html}</table>"))[0]
    # Flatten multi-level columns if any
    df.columns = df.columns.get_level_values(0)
    # or combine levels (optional)
    # df.columns = df.columns.map('_'.join)
    # Remove columns where any cell contains "Upgrade"
    for col in df.columns:
        if (df[col] == 'Upgrade').any():
            df = df.drop(columns=[col])
    return df


class FinancialReportFetcher:
    def __init__(self, context: BrowserContext, ticker: str, href: str):
        self.context = context
        self.ticker = ticker
        self.href = href

    async def _fetch_report(self, report_type: str):
        # Create a new page for this report
        page = await self.context.new_page()
        helper = PageHelper(page)

        try:
            await helper.navigate(f"https://stockanalysis.com{self.href}{FINANCIAL_ROUTES[report_type]}")
            await close_popup(page)
            df = await extract_table_to_csv(page, "table.financials-table")

            # Save to data directory
            os.makedirs("data", exist_ok=True)
            os.makedirs(f"data/{self.ticker}", exist_ok=True)
            df.to_csv(f"data/{self.ticker}/{report_type}.csv", index=False)
            return df
        finally:
            # Always close the page after extraction
            await page.close()

    async def income_statement(self):
        df = await self._fetch_report("income")
        wanted_rows = ['Net Income Growth', 'Operating Margin', 'Profit Margin']
        df_filtered = df[df.iloc[:, 0].isin(wanted_rows)]
        df_filterd_md = df_filtered.to_markdown(index=False)
        net_income_consistency = get_row_consistency(wanted_rows[0], df)
        operating_margin_consistency = get_row_consistency(wanted_rows[1], df)
        profit_margin_values = parse_row_percentages('Profit Margin', df)
        profit_margin_avg = profit_margin_values.mean()
        rows_to_add = []
        net_income_consistency = f"**{wanted_rows[0]} Consistency:** {net_income_consistency:.2f}"
        operating_margin_consistency = f"**{wanted_rows[1]} Consistency:** {operating_margin_consistency:.2f}"
        profit_margin_avg = f"**Average {wanted_rows[2]}:** {profit_margin_avg:.2f}%"
        rows_to_add.extend([net_income_consistency, operating_margin_consistency, profit_margin_avg])
        df_filterd_md += f"\n\n{net_income_consistency}\n{operating_margin_consistency}\n{profit_margin_avg}\n"
        return df_filterd_md  
    
    async def balance_sheet(self):
        df = await self._fetch_report("balance-sheet")
        wanted_rows = ['Long-Term Debt', 'Working Capital']
        df_filtered = df[df.iloc[:, 0].isin(wanted_rows)]
        df_filterd_md = df_filtered.to_markdown(index=False)
        last_year_column_name = sorted([c for c in df_filtered.columns if c.startswith('FY ')], reverse=True)[0]
        last_year_working_capital = safe_get_numeric_value(df, 'Working Capital', last_year_column_name)
        last_year_debt = safe_get_numeric_value(df, 'Long-Term Debt', last_year_column_name)
        df_filterd_md += f"\n\n**Working Capital - Long-Term Debt (Last Year):** {last_year_working_capital - last_year_debt}\n\n"
        return df_filterd_md
    
    async def cash_flow(self):
        return await self._fetch_report("cash-flow")
    
    async def ratios(self):
        df = await self._fetch_report("ratios")
        wanted_rows = ['Return on Equity (ROE)', 'Current Ratio']
        df_filtered = df[df.iloc[:, 0].isin(wanted_rows)]
        df_filterd_md = df_filtered.to_markdown(index=False)
        roe_values = parse_row_percentages('Return on Equity (ROE)', df)
        roe_avg = roe_values.mean()
        df_filterd_md += f"\n\n**Average Return on Equity (ROE):** {roe_avg:.2f}%\n"
        return df_filterd_md  
    
async def stock_finantial_filters(context: BrowserContext, ticker: str, href: str):
    finiatial_summary_path = f"data/{ticker}/financial_summary.md"
    if os.path.exists(finiatial_summary_path):
        print(f"Financial summary for {ticker} already exists. Skipping.")
        return
    # Use class-based approach with parallel execution
    fetcher = FinancialReportFetcher(context, ticker, href)
    income_md, balance_md, ratios_md = await asyncio.gather(
        fetcher.income_statement(),
        fetcher.balance_sheet(),
        fetcher.ratios()
    )

    full_report = f"""## Financial Summary for {ticker}

### Income Statement Highlights
{income_md}

### Balance Sheet Highlights
{balance_md}

### Key Ratios
{ratios_md}

"""
    with open(f"data/{ticker}/financial_summary.md", "w") as f:
        f.write(full_report)

    await asyncio.sleep(1)  # brief pause to ensure all file operations complete