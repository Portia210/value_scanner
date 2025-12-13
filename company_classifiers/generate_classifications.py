import json
import pandas as pd
import re
from pathlib import Path
from config import DATA_DIR, EXISTING_STOCKS_FILE_PATH, OUTPUT_DIR
from enums import IncomeIndex
from company_classifiers.main import classify_company
from reports_checks.formula_helpers import calculate_cagr, calculate_earnings_volatility
from utils.logger import get_logger

logger = get_logger()

def generate_classification_csv():
    """
    Batches process all companies, runs advanced classification, and exports to CSV.
    This CSV acts as the Source of Truth for the Report Maker.
    """
    logger.info("Starting Batch Classification Generation...")
    
    try:
        if not EXISTING_STOCKS_FILE_PATH.exists():
            logger.error(f"Stocks file not found: {EXISTING_STOCKS_FILE_PATH}")
            return

        with open(EXISTING_STOCKS_FILE_PATH, 'r') as f:
            companies = json.load(f)
    except Exception as e:
        logger.error(f"Error loading stocks file: {e}")
        return

    results = []
    
    for symbol, data in companies.items():
        sector = data.get("sector", "Unknown")
        industry = data.get("industry", "Unknown")
        beta = data.get("beta") 
        
        income_csv_path = DATA_DIR / symbol / "income.csv"
        
        cagr = None
        rev_cagr = None
        volatility = 0.0

        if income_csv_path.exists():
            try:
                income_df = pd.read_csv(income_csv_path, index_col=0)
                # Filter FY columns
                last_5_years_cols = [col for col in income_df.columns if re.match(r'FY 20\d{2}', col)][:5]
                last_5_years_cols.sort(reverse=True)
                
                # Calculate Metrics
                # Use 3-Year CAGR for Growth (EPS and Revenue)
                cagr = calculate_cagr(income_df, IncomeIndex.EPS_DILUTED, last_5_years_cols, years=3)
                rev_cagr = calculate_cagr(income_df, IncomeIndex.REVENUE, last_5_years_cols, years=3)
                volatility = calculate_earnings_volatility(income_df, IncomeIndex.EPS_DILUTED, last_5_years_cols)
            except Exception as e:
                logger.warning(f"Error calculating metrics for {symbol}: {e}")

        # Run Modular Classification
        classification = classify_company(
            sector=sector,
            industry=industry,
            cagr_3yr=cagr,
            revenue_cagr_3yr=rev_cagr,
            volatility=volatility,
            beta=beta
        )

        results.append({
            "Symbol": symbol,
            "Sector": sector,
            "Industry": industry,
            "EPS CAGR 3Y": f"{cagr:.2f}" if cagr is not None else "N/A",
            "Rev CAGR 3Y": f"{rev_cagr:.2f}" if rev_cagr is not None else "N/A",
            "Volatility (CV)": f"{volatility:.2f}",
            "Type": classification["type"],
            "Valuation Method": classification["valuation_method"],
            "Reasons": ", ".join(classification["reasons"])
        })

    # Export to CSV
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    output_path = OUTPUT_DIR / "company_classifications.csv"
    df = pd.DataFrame(results)
    
    # Sort by Type then Symbol
    if not df.empty:
        df.sort_values(by=["Type", "Symbol"], ascending=[True, True], inplace=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Classification CSV generated at {output_path} ({len(df)} companies)")
    else:
        logger.warning("No classification results generated.")

if __name__ == "__main__":
    generate_classification_csv()
