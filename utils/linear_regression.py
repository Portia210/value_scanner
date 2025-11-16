import numpy as np
import pandas as pd
from scipy.stats import linregress

def get_row_consistency(row_name, df: pd.DataFrame):
    """Main function: return consistency analysis for a row"""
    values = parse_row_percentages(row_name, df)
    y_data = np.array(values)
    valid_mask = ~np.isnan(y_data)

    if not np.any(valid_mask) or np.sum(valid_mask) < 2:
        return 0.0  # Return 0.0 for insufficient data instead of string

    x_data = np.arange(len(y_data))[valid_mask]
    y_clean = y_data[valid_mask]

    # Linear regression
    _, _, r_value, _, _ = linregress(x_data, y_clean)
    r_squared = r_value ** 2

    return r_squared.round(2)





def detailed_analysis(row_name, csv_path='data/ANET/income.csv'):
    """Detailed analysis with all statistics"""
    df = pd.read_csv(csv_path)
    values = parse_row_percentages(row_name, df)
    y_data = np.array(values)
    valid_mask = ~np.isnan(y_data)

    if not np.any(valid_mask) or np.sum(valid_mask) < 2:
        print(f"\n❌ {row_name}: Insufficient data")
        return

    x_data = np.arange(len(y_data))[valid_mask]
    y_clean = y_data[valid_mask]

    slope, _, r_value, _, _ = linregress(x_data, y_clean)
    r_squared = r_value ** 2

    print(f"\n📊 {row_name}")
    print(f"   Data: {', '.join([f'{v:.1f}%' for v in y_data if not np.isnan(v)])}")
    print(f"   Trend: {slope:+.2f}% per year")
    print(f"   Consistency: {r_squared:.3f}")

    if r_squared > 0.8:
        consistency = "🟢 Very consistent"
    elif r_squared > 0.5:
        consistency = "🟡 Moderately consistent"
    else:
        consistency = "🔴 Inconsistent"

    print(f"   Analysis: {consistency}")

    if abs(slope) > 1:
        if slope > 0:
            print(f"   📈 Strong upward trend")
        else:
            print(f"   📉 Strong downward trend")
    else:
        print(f"   ➡️ Relatively stable")

if __name__ == "__main__":
    detailed_analysis('Net Income Growth', 'data/ANET/income.csv')
    detailed_analysis('Revenue Growth (YoY)', 'data/ANET/income.csv')
    detailed_analysis('Profit Margin', 'data/ANET/income.csv')