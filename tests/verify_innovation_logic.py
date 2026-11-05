
import pandas as pd
import unittest
from reports_checks.ken_fisher_check import ken_fisher_check
from enums import IncomeIndex, RatiosIndex

# Mock Enums if they aren't available in the test env context easily, 
# but assuming we can import them as they are in the project structure.
# If not, I'll define dummies, but let's try importing first as the environment seems set up.

class TestInnovationCheck(unittest.TestCase):
    def setUp(self):
        # Setup basic dataframes with 5 years of columns
        self.cols = ['2024', '2023', '2022', '2021', '2020']
        self.income_df = pd.DataFrame(index=[
            IncomeIndex.RESEARCH_AND_DEVELOPMENT.value,
            IncomeIndex.REVENUE.value,
            IncomeIndex.PROFIT_MARGIN_PERCENT.value,
            IncomeIndex.EPS_DILUTED.value,
            IncomeIndex.FREE_CASH_FLOW_PER_SHARE.value
        ], columns=self.cols)
        
        self.ratios_df = pd.DataFrame(index=[
            RatiosIndex.MARKET_CAPITALIZATION.value,
            RatiosIndex.PS_RATIO.value,
            RatiosIndex.PE_RATIO.value,
            RatiosIndex.P_OCF_RATIO.value,
            RatiosIndex.DEBT_EQUITY_RATIO.value,
            RatiosIndex.PB_RATIO.value # Added for safety if needed
        ], columns=self.cols)
        
        # Fill Default "Good" values for non-innovation checks to isolate innovation logic
        self.ratios_df.ffill(axis=1, inplace=True)
        self.ratios_df.fillna(0, inplace=True) # Clear NaNs
        
        # Defaults for passing other checks
        self.ratios_df.loc[RatiosIndex.PS_RATIO.value] = 1.0
        self.ratios_df.loc[RatiosIndex.DEBT_EQUITY_RATIO.value] = 0.1
        self.ratios_df.loc[RatiosIndex.P_OCF_RATIO.value] = 10.0 # < 25
        self.ratios_df.loc[RatiosIndex.PE_RATIO.value] = 10.0 # < 40
        self.income_df.loc[IncomeIndex.PROFIT_MARGIN_PERCENT.value] = 20.0
        
        # Set Growing EPS: 2020=10, ..., 2024=20
        # Columns: ['2024', '2023', '2022', '2021', '2020']
        # We can set specific values
        self.income_df.loc[IncomeIndex.EPS_DILUTED.value, '2020'] = 10.0
        self.income_df.loc[IncomeIndex.EPS_DILUTED.value, '2024'] = 20.0
        # Fill others to avoid N/A if checked (helper uses 2024 and 2020 mostly)
        self.income_df.loc[IncomeIndex.EPS_DILUTED.value] = self.income_df.loc[IncomeIndex.EPS_DILUTED.value].fillna(15.0)

        self.income_df.loc[IncomeIndex.FREE_CASH_FLOW_PER_SHARE.value] = 5.0

    def test_tech_pass(self):
        # Tech: P/R&D between 5 and 15
        # Market Cap 100, R&D 10 => P/R&D 10 (Pass)
        self.ratios_df.loc[RatiosIndex.MARKET_CAPITALIZATION.value] = 100.0
        self.income_df.loc[IncomeIndex.RESEARCH_AND_DEVELOPMENT.value] = 10.0
        self.income_df.loc[IncomeIndex.REVENUE.value] = 100.0 
        
        res_str, passed = ken_fisher_check(
            "TEST", 
            self.income_df, 
            self.ratios_df.copy(), 
            self.ratios_df.copy(), 
            self.cols, 
            classification_res={"type": "Tech/Pharma"}
        )
        self.assertIn("Innovation Factor", res_str)
        self.assertIn("(Tech/Pharma)", res_str)
        self.assertIn("P/R&D", res_str)
        self.assertIn("10.0", res_str) # Value check
        self.assertTrue(passed)

    def test_tech_fail_high_prr(self):
        # Market Cap 200, R&D 10 => P/R&D 20 (Fail > 15)
        self.ratios_df.loc[RatiosIndex.MARKET_CAPITALIZATION.value] = 200.0
        self.income_df.loc[IncomeIndex.RESEARCH_AND_DEVELOPMENT.value] = 10.0
        
        res_str, passed = ken_fisher_check(
            "TEST", 
            self.income_df, 
            self.ratios_df, 
            self.ratios_df, 
            self.cols, 
            classification_res={"type": "Tech/Pharma"}
        )
        self.assertFalse(passed) 
        self.assertIn("Innovation Factor", res_str)
        self.assertIn("(Tech/Pharma)", res_str)
        self.assertIn("P/R&D", res_str)

    def test_other_pass(self):
        # Other: Avg R&D/Rev > 10%
        # Year 1: 12/100 = 12%
        # Year 2 ... 5: 12%
        self.income_df.loc[IncomeIndex.RESEARCH_AND_DEVELOPMENT.value] = 12.0
        self.income_df.loc[IncomeIndex.REVENUE.value] = 100.0
        
        res_str, passed = ken_fisher_check(
            "TEST", 
            self.income_df, 
            self.ratios_df, 
            self.ratios_df, 
            self.cols, 
            classification_res={"type": "Defensive"}
        )
        self.assertTrue(passed)
        self.assertIn("(Standard)", res_str)
        self.assertIn("Avg R&D/Rev", res_str)
        self.assertIn("12.0%", res_str)
        # Check for Trend string presence
        self.assertIn("12.0%", res_str) 

    def test_other_fail(self):
        # Other: Avg R&D/Rev 5%
        self.income_df.loc[IncomeIndex.RESEARCH_AND_DEVELOPMENT.value] = 5.0
        self.income_df.loc[IncomeIndex.REVENUE.value] = 100.0
        
        res_str, passed = ken_fisher_check(
            "TEST", 
            self.income_df, 
            self.ratios_df, 
            self.ratios_df, 
            self.cols, 
             classification_res={"type": "Defensive"}
        )
        self.assertFalse(passed)
        self.assertIn("5.0%", res_str)

    def test_missing_data(self):
        # Set R&D to None/NaN
        self.income_df.loc[IncomeIndex.RESEARCH_AND_DEVELOPMENT.value] = None
        
        res_str, passed = ken_fisher_check(
            "TEST", 
            self.income_df, 
            self.ratios_df, 
            self.ratios_df, 
            self.cols, 
             classification_res={"type": "Defensive"}
        )
        self.assertTrue(passed)
        self.assertIn("N/A", res_str)
        self.assertIn("Missing", res_str)

if __name__ == '__main__':
    unittest.main()
