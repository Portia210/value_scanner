from pathlib import Path
import os

# Base Directories
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Input Files
COOKIES_FILE_PATH = BASE_DIR / "cookies.txt"
EXISTING_STOCKS_FILE_PATH = OUTPUT_DIR / "filtered_companies.json"

# Output Files
FILTERS_CSV_PATH = OUTPUT_DIR / "filters_results.csv"
NEW_COMPANIES_FILE_PATH = OUTPUT_DIR / "new_companies.md"

# Other constants
SCREENER_URL = "https://stockanalysis.com/stocks/screener/"

from enum import Enum

class CsvFiles(Enum):
    INCOME = "income"
    BALANCE_SHEET = "balance-sheet"
    CASH_FLOW = "cash-flow"
    RATIOS = "ratios"
