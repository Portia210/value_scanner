from utils.linear_regression import get_row_consistency
from utils.pd_parser import parse_row_percentages
from utils.financial_helpers import safe_get_numeric_value
from enum import Enum

percent_suffix = " (%)"

class incomeRows(Enum):
    NET_INCOME_GROWTH = "Net Income Growth" + percent_suffix
    OPERATING_MARGIN = "Operating Margin" + percent_suffix
    PROFIT_MARGIN = "Profit Margin" + percent_suffix
    REVENUE = "Revenue"
    EPS = "EPS (Diluted)"
    
class balanceSheetRows(Enum):
    WORKING_CAPITAL = "Working Capital"
    LONG_TERM_DEBT = "Long-Term Debt"
    
class ratiosRows(Enum):
    CURRENT_RATIO = "Current Ratio"
    ROE = "Return on Equity (ROE)" + percent_suffix
    PE_RATIO = "PE Ratio"
    PB_RATIO = "PB Ratio"
    POCF_RATIO = "P/OCF Ratio"
    
    
    
    
def check_df_for_missing_rows(df, required_rows):
    missing_rows = [row.value for row in required_rows if row.value not in df.index]
    if missing_rows:
        logger.warning(f"Missing rows: {missing_rows}")


def validate_all_csvs(ticker):
    files_paths = get_csv_files_paths(ticker, cleaned=True)
    income_csv = pd.read_csv(files_paths["income"], index_col=0)
    check_df_for_missing_rows(income_csv, incomeRows)
    ratios_csv = pd.read_csv(files_paths["ratios"], index_col=0)
    check_df_for_missing_rows(ratios_csv, ratiosRows)
    balance_csv = pd.read_csv(files_paths["balance"], index_col=0)
    check_df_for_missing_rows(balance_csv, balanceSheetRows)


class ReportMaker:
    async def income_statement(self, df):
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
    
    async def balance_sheet(self, df):
        wanted_rows = ['Long-Term Debt', 'Working Capital']
        df_filtered = df[df.iloc[:, 0].isin(wanted_rows)]
        df_filterd_md = df_filtered.to_markdown(index=False)
        last_year_column_name = sorted([c for c in df_filtered.columns if c.startswith('FY ')], reverse=True)[0]
        last_year_working_capital = safe_get_numeric_value(df, 'Working Capital', last_year_column_name)
        last_year_debt = safe_get_numeric_value(df, 'Long-Term Debt', last_year_column_name)
        df_filterd_md += f"\n\n**Working Capital - Long-Term Debt (Last Year):** {last_year_working_capital - last_year_debt}\n\n"
        return df_filterd_md
    
    async def cash_flow(self, df):
        return await self._fetch_report("cash-flow")
    
    async def ratios(self, df):
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

    income_md, balance_md, ratios_md = "", "", ""

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
