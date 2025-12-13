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

def test_modular_classification():
    try:
        with open(EXISTING_STOCKS_FILE_PATH, 'r') as f:
            companies = json.load(f)
    except Exception as e:
        logger.error(f"Error loading stocks file: {e}")
        return

    results = []
    print(f"Processing {len(companies)} companies with Final Advanced Logic...")

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
                logger.error(f"Error processing {symbol} data: {e}")

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
    output_path = OUTPUT_DIR / "company_classifications.csv"
    df = pd.DataFrame(results)
    
    # Sort by Type then Symbol
    df.sort_values(by=["Type", "Symbol"], ascending=[True, True], inplace=True)
    
    df.to_csv(output_path, index=False)
    print(f"\nFinal Results saved to {output_path}")
    
    # Print Summary
    print("\n--- Final Classification Summary ---")
    print(df['Type'].value_counts().to_markdown())
    
    # Print Sample of each type
    print("\n--- Sample: Defensive (Insurance Lock Check) ---")
    ins = df[df['Industry'].str.contains('Insurance', na=False)].head(5)
    if not ins.empty:
        print(ins[['Symbol', 'Industry', 'Type', 'Reasons']].to_markdown(index=False))

if __name__ == "__main__":
    test_modular_classification()
