from value_scanner.analysis import rows as R
from value_scanner.analysis.debt import long_term_debt


def getter(**values):
    mapping = {getattr(R, k): v for k, v in values.items()}
    return mapping.get


def test_uses_the_row_when_present():
    assert long_term_debt(getter(LONG_TERM_DEBT=40.0, TOTAL_DEBT=100.0)) == 40.0
    assert long_term_debt(getter(LONG_TERM_DEBT=0.0, TOTAL_DEBT=100.0)) == 0.0


def test_fallback_subtracts_current_parts():
    g = getter(
        TOTAL_DEBT=100.0, CURRENT_PORTION_LTD=10.0, SHORT_TERM_DEBT=5.0, CURRENT_PORTION_LEASES=3.0
    )
    assert long_term_debt(g) == 82.0


def test_fallback_never_negative_and_unknown_is_none():
    assert long_term_debt(getter(TOTAL_DEBT=5.0, SHORT_TERM_DEBT=9.0)) == 0.0
    assert long_term_debt(getter()) is None
    assert long_term_debt(getter(LONG_TERM_DEBT=None)) is None
