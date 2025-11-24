from enum import Enum 

EXISTING_STOCKS_FILE_PATH = "filtered_companies.json"
NEW_COMPANIES_FILE_PATH = "new_companies.md"


class CsvFiles(Enum):
    RATIOS = "ratios"
    INCOME = "income"
    BALANCE = "balance-sheet"
    CASHFLOW = "cash-flow"
