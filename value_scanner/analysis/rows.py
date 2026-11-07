"""Row names exactly as StockAnalysis shows them (checked against live pages, 2026-11-05).

A name that is not on a stock's page simply gives None from `Statements` (-> NA). If the site
renames a row, every stock turns NA for that criterion: watch for it (GOTCHAS).
"""

REVENUE = "Revenue"
NET_INCOME = "Net Income"
EPS_DILUTED = "EPS (Diluted)"
OPERATING_INCOME = "Operating Income"
PROFIT_MARGIN_PCT = "Profit Margin (%)"
GROSS_PROFIT = "Gross Profit"
RESEARCH_AND_DEVELOPMENT = "Research & Development"
SHARES_DILUTED = "Shares Outstanding (Diluted)"

TOTAL_ASSETS = "Total Assets"
TOTAL_CURRENT_ASSETS = "Total Current Assets"
TOTAL_CURRENT_LIABILITIES = "Total Current Liabilities"
TOTAL_LIABILITIES = "Total Liabilities"
TOTAL_DEBT = "Total Debt"
LONG_TERM_DEBT = "Long-Term Debt"
EQUITY = "Shareholders' Equity"
RETAINED_EARNINGS = "Retained Earnings"

OPERATING_CASH_FLOW = "Operating Cash Flow"
CAPEX = "Capital Expenditures"
FREE_CASH_FLOW = "Free Cash Flow"
