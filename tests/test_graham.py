import pytest

from value_scanner.analysis import rows as R
from value_scanner.analysis.criteria import Status
from value_scanner.analysis.gurus.graham import evaluate_graham
from value_scanner.analysis.statements import Statements

YEARS = [2025, 2024, 2023, 2022, 2021]


def stmts(**series):
    data = []
    for item, vals in series.items():
        ttm = None
        if isinstance(vals, dict):
            ttm, vals = vals.get("TTM"), vals["FY"]
        if ttm is not None:
            data.append((item, "TTM", ttm))
        data += [(item, f"FY {y}", v) for y, v in zip(YEARS, vals, strict=False)]
    return Statements(data)


GOOD = {
    R.REVENUE: [400.0, 380.0, 360.0, 340.0, 320.0],
    R.EPS_DILUTED: [3.0, 2.8, 2.0, 1.6, 1.4],
    R.TOTAL_CURRENT_ASSETS: {"TTM": 500.0, "FY": [500.0] * 5},
    R.TOTAL_CURRENT_LIABILITIES: {"TTM": 200.0, "FY": [200.0] * 5},
    R.LONG_TERM_DEBT: {"TTM": 100.0, "FY": [100.0] * 5},
}


def run(pe=10.0, pb=1.5, pe_limit=15.0, **overrides):
    data = {**GOOD, **overrides}
    return {r.criterion_id: r for r in evaluate_graham(stmts(**data), pe, pb, pe_limit)}


def test_good_stock_passes_all_six():
    res = run()
    assert len(res) == 6 and {r.status for r in res.values()} == {Status.PASS}
    assert res["graham_number"].value == pytest.approx(15.0)
    assert res["working_capital"].value == pytest.approx(200.0)  # 300 - 100
    assert res["eps_growth"].value == pytest.approx((2.9 / 1.5 - 1) * 100)


def test_sales_boundary():
    assert run(**{R.REVENUE: [350.0] * 5})["sales"].status == Status.FAIL  # not above
    assert run(**{R.REVENUE: [350.01] * 5})["sales"].status == Status.PASS
    assert run(**{R.REVENUE: [None] * 5})["sales"].status == Status.NA


def test_current_ratio_boundary():
    at = run(**{R.TOTAL_CURRENT_ASSETS: {"TTM": 400.0, "FY": [400.0] * 5}})["current_ratio"]
    assert at.status == Status.FAIL
    zero = run(**{R.TOTAL_CURRENT_LIABILITIES: {"TTM": 0.0, "FY": [0.0] * 5}})["current_ratio"]
    assert zero.status == Status.NA


def test_working_capital_vs_long_term_debt():
    equal = run(**{R.LONG_TERM_DEBT: {"TTM": 300.0, "FY": [300.0] * 5}})["working_capital"]
    assert equal.status == Status.FAIL  # must be greater
    neg = run(**{R.TOTAL_CURRENT_ASSETS: {"TTM": 100.0, "FY": [100.0] * 5}})["working_capital"]
    assert neg.status == Status.FAIL and neg.value < 0


def test_working_capital_without_long_term_debt_row_means_no_long_term_debt():
    no_lt = {
        R.LONG_TERM_DEBT: {"FY": [None] * 5},
        R.TOTAL_ASSETS: {"TTM": 900.0, "FY": [900.0] * 5},
    }
    r = run(**no_lt)["working_capital"]
    assert r.status == Status.PASS and r.value == pytest.approx(300.0)  # 300 - 0
    # Total Debt (e.g. leases) is not used as a substitute
    r = run(**no_lt, **{R.TOTAL_DEBT: {"TTM": 350.0, "FY": [350.0] * 5}})["working_capital"]
    assert r.status == Status.PASS and r.value == pytest.approx(300.0)


def test_working_capital_unknown_without_a_balance_sheet():
    data = {k: v for k, v in GOOD.items() if k != R.LONG_TERM_DEBT}
    res = {r.criterion_id: r for r in evaluate_graham(stmts(**data), 10.0, 1.5)}
    assert res["working_capital"].status == Status.NA


@pytest.mark.parametrize(
    ("pe", "status"),
    [
        (14.99, Status.PASS),
        (15.0, Status.FAIL),
        (0.0, Status.FAIL),
        (-8.0, Status.FAIL),
        (None, Status.NA),
    ],
)
def test_pe_limit(pe, status):
    assert run(pe=pe)["pe"].status == status


def test_negative_pe_is_not_a_pass_even_though_it_is_below_the_limit():
    r = run(pe=-8.0)["pe"]
    assert r.status == Status.FAIL and r.strength == 0.0 and "<= 0" in r.note


def test_tech_limit_variant():
    assert run(pe=20.0, pe_limit=25.0)["pe"].status == Status.PASS
    assert run(pe=20.0)["pe"].status == Status.FAIL


def test_graham_number_boundaries():
    assert run(pe=11.0, pb=2.0)["graham_number"].status == Status.FAIL  # 22 exactly
    assert run(pe=10.9, pb=2.0)["graham_number"].status == Status.PASS
    assert run(pe=10.0, pb=None)["graham_number"].status == Status.NA
    neg = run(pe=-1.0, pb=-5.0)["graham_number"]  # product is +5 but both factors are negative
    assert neg.status == Status.FAIL


def test_eps_growth_boundary_and_loss_year():
    # mean(last two) / mean(first two) = 1.3 exactly -> not above 30%
    at = run(**{R.EPS_DILUTED: [1.3, 1.3, 1.0, 1.0, 1.0]})["eps_growth"]
    assert at.value == pytest.approx(30.0) and at.status == Status.FAIL
    loss = run(**{R.EPS_DILUTED: [3.0, 2.8, -0.1, 1.6, 1.4]})["eps_growth"]
    assert loss.status == Status.FAIL and "loss" in loss.note
    missing = run(**{R.EPS_DILUTED: [3.0, 2.8, None, 1.6, 1.4]})["eps_growth"]
    assert missing.status == Status.NA
    loss_beats_missing = run(**{R.EPS_DILUTED: [3.0, -2.0, None, 1.6, 1.4]})["eps_growth"]
    assert loss_beats_missing.status == Status.FAIL
    decline = run(**{R.EPS_DILUTED: [1.0, 1.0, 1.5, 2.0, 2.0]})["eps_growth"]
    assert decline.status == Status.FAIL and decline.value < 0


def test_empty_statements_are_na_except_multiples():
    res = {r.criterion_id: r for r in evaluate_graham(Statements([]), None, None)}
    assert {r.status for r in res.values()} == {Status.NA}
