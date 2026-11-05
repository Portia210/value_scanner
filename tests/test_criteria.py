import math

import pytest

from value_scanner.analysis.criteria import Criterion, Status, compare, evaluate, strength
from value_scanner.analysis.statements import Statements
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

C_GT = Criterion("t1", "graham", 4, "t", "x > 10", ">", 10.0)
C_LT = Criterion("t2", "graham", 4, "t", "x < 10", "<", 10.0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (12.0, 1.0),  # exactly 20% of the threshold above it: comfortable
        (11.99, 0.75),
        (10.01, 0.75),
        (10.0, 0.25),  # at the threshold a strict '>' fails, narrowly
        (8.01, 0.25),
        (8.0, 0.0),  # exactly 20% below: no longer "narrow"
        (-5.0, 0.0),
    ],
)
def test_strength_greater_than(value, expected):
    assert strength(value, 10.0, ">") == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(8.0, 1.0), (8.01, 0.75), (9.99, 0.75), (10.0, 0.25), (11.99, 0.25), (12.0, 0.0), (50, 0.0)],
)
def test_strength_less_than(value, expected):
    assert strength(value, 10.0, "<") == expected


def test_inclusive_directions_pass_at_the_threshold():
    assert strength(10.0, 10.0, ">=") == 0.75
    assert strength(10.0, 10.0, "<=") == 0.75


def test_threshold_zero_has_no_narrow_band():
    assert strength(0.1, 0.0, ">") == 1.0
    assert strength(0.0, 0.0, ">") == 0.0
    assert strength(-0.1, 0.0, ">") == 0.0


def test_negative_threshold_margin_uses_absolute_value():
    assert strength(-8.0, -10.0, ">") == 1.0  # 2 above, margin 2
    assert strength(-9.0, -10.0, ">") == 0.75


def test_evaluate_pass_fail():
    assert evaluate(C_GT, 15).status == Status.PASS
    assert evaluate(C_GT, 10).status == Status.FAIL
    r = evaluate(C_LT, 9)
    assert (r.status, r.value, r.threshold, r.strength) == (Status.PASS, 9, 10.0, 0.75)


@pytest.mark.parametrize("missing", [None, math.nan])
def test_missing_is_na_never_pass(missing):
    r = evaluate(C_GT, missing)
    assert r.status == Status.NA and r.strength is None and r.value is None


def test_result_row_matches_repository_shape():
    row = evaluate(C_GT, 15).as_row()
    assert row["status"] == "PASS" and row["guru"] == "graham" and row["criterion_id"] == "t1"


def test_compare():
    assert compare("piotroski", "p1", 5, 3).status == Status.PASS
    assert compare("piotroski", "p1", 3, 3).status == Status.FAIL  # equal is not better
    assert compare("piotroski", "p1", -1, -2).strength == 1.0  # negative values compare fine
    assert compare("piotroski", "p1", None, 3).status == Status.NA
    assert compare("piotroski", "p1", 3, math.nan).status == Status.NA


# ── Statements ──────────────────────────────────────────────────────────────────────────────
ROWS = [
    ("Revenue", "TTM", 1932.0),
    ("Revenue", "FY 2025", 1700.0),
    ("Revenue", "FY 2024", 1201.0),
    ("Revenue", "FY 2023", 1169.0),
    ("Net Income", "FY 2025", None),
    ("Net Income", "FY 2024", 168.5),
    ("Debt", "FY 2025", math.nan),
]


def test_statements_accessors():
    s = Statements(ROWS)
    assert s.years() == [2025, 2024, 2023]
    assert (s.fy("Revenue"), s.fy("Revenue", 1), s.fy("Revenue", 2)) == (1700.0, 1201.0, 1169.0)
    assert s.ttm("Revenue") == 1932.0 and s.current("Revenue") == 1932.0
    assert s.series("Revenue", 4) == [1700.0, 1201.0, 1169.0, None]


def test_missing_values_are_none_not_zero():
    s = Statements(ROWS)
    assert s.fy("Net Income") is None and s.fy("Debt") is None  # None and NaN
    assert s.fy("Nope") is None and s.ttm("Net Income") is None
    assert s.fy("Revenue", 10) is None
    assert s.current("Net Income") is None  # no TTM and the latest FY is missing
    assert s.has("Revenue") and not s.has("Nope")


def test_current_falls_back_to_latest_fy():
    s = Statements([("X", "FY 2025", 5.0), ("X", "FY 2024", 4.0)])
    assert s.current("X") == 5.0


def test_from_repo_merges_statements_and_uses_latest_fetch():
    repo = Repository(db.open_database(":memory:"))
    repo.upsert_company("AAA")
    repo.save_statement_fetch("AAA", "income", "sa", "ok", [("Revenue", "FY 2024", 1.0)])
    repo.save_statement_fetch("AAA", "income", "sa", "ok", [("Revenue", "FY 2024", 2.0)])
    repo.save_statement_fetch(
        "AAA", "balance_sheet", "sa", "ok", [("Total Assets", "FY 2024", 9.0)]
    )
    repo.save_statement_fetch("AAA", "cash_flow", "sa", "blocked")
    s = Statements.from_repo(repo, "AAA")
    assert s.fy("Revenue") == 2.0 and s.fy("Total Assets") == 9.0
    assert Statements.from_repo(repo, "ZZZ").years() == []


def test_float_noise_does_not_flip_a_boundary():
    c = Criterion("t", "graham", 4, "t", "x > 30", ">", 30.0)
    assert evaluate(c, (1.3 / 1.0 - 1) * 100).status == Status.FAIL  # 30.000000000000004
