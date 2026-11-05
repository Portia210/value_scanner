from value_scanner.analysis import rows as R
from value_scanner.analysis.debt import long_term_debt


def getter(**values):
    mapping = {getattr(R, k): v for k, v in values.items()}
    return mapping.get


def test_uses_the_row_when_present():
    assert long_term_debt(getter(LONG_TERM_DEBT=40.0, TOTAL_ASSETS=900.0)) == 40.0
    assert long_term_debt(getter(LONG_TERM_DEBT=0.0, TOTAL_ASSETS=900.0)) == 0.0


def test_no_row_means_no_debt_when_the_balance_sheet_exists():
    # even if Total Debt shows leases or short-term debt: no substitute formula
    assert long_term_debt(getter(TOTAL_ASSETS=900.0)) == 0.0
    assert long_term_debt(getter(TOTAL_ASSETS=900.0, TOTAL_DEBT=120.0)) == 0.0


def test_no_balance_sheet_is_unknown_not_zero():
    assert long_term_debt(getter()) is None
    assert long_term_debt(getter(TOTAL_DEBT=50.0)) is None
