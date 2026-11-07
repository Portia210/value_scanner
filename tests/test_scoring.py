import pytest

from value_scanner.analysis.criteria import Result, Status
from value_scanner.analysis.scoring import (
    GuruScore,
    guru_score,
    is_candidate,
    opportunity,
    opportunity_components,
    quality,
)


def res(status, strength=None):
    return Result("g", "c", Status(status), strength=strength)


def test_guru_score_is_mean_strength_of_computed_criteria():
    g = guru_score([res("PASS", 1.0), res("PASS", 0.75), res("FAIL", 0.25), res("FAIL", 0.0)])
    assert g.score == pytest.approx(0.5) and g.coverage == 1.0 and (g.passed, g.total) == (2, 4)


def test_na_is_excluded_from_the_score_and_lowers_coverage():
    g = guru_score([res("PASS", 1.0), res("PASS", 1.0), res("PASS", 0.75), res("NA"), res("NA")])
    assert g.score == pytest.approx(2.75 / 3) and g.coverage == pytest.approx(0.6)


def test_coverage_below_60_percent_is_not_ranked():
    g = guru_score([res("PASS", 1.0), res("NA"), res("NA")])
    assert g.score is None and g.coverage == pytest.approx(1 / 3)
    assert guru_score([res("NA")] * 4).score is None
    assert guru_score([]).score is None and guru_score([]).coverage == 0.0


def test_all_failing_scores_zero_not_none():
    assert guru_score([res("FAIL", 0.0)] * 3).score == 0.0


def test_quality_averages_ranked_gurus_and_needs_two():
    s = {"a": GuruScore(1.0, 1, 1, 1), "b": GuruScore(0.5, 1, 1, 1), "c": GuruScore(None, 0, 0, 1)}
    assert quality(s) == pytest.approx(0.75)
    assert quality({"a": GuruScore(1.0, 1, 1, 1), "c": GuruScore(None, 0, 0, 1)}) is None
    assert quality({}) is None


def comps(**kw):
    base = {"pe": 10.0, "pb": 1.0, "ps": 1.0, "pe_5y": 20.0, "tech": False, "cyclical": False}
    return opportunity_components(**{**base, **kw})


def test_components_formulas():
    c = comps()
    assert c["graham_number"] == pytest.approx(1 - (10 / 22.5) ** 0.5)
    assert c["fair_pe"] == pytest.approx(1 - 10 / 15)
    assert c["vs_history"] == pytest.approx(0.5)
    assert c["price_sales"] == pytest.approx(1 - 1 / 1.5)


def test_technology_uses_pe_25_and_skips_graham_and_sales():
    c = comps(tech=True)
    assert c["graham_number"] is None and c["price_sales"] is None
    assert c["fair_pe"] == pytest.approx(1 - 10 / 25)


def test_cyclical_uses_the_stricter_sales_limit():
    assert comps(cyclical=True)["price_sales"] == pytest.approx(1 - 1 / 0.8)


@pytest.mark.parametrize("pe", [None, 0.0, -5.0])
def test_non_positive_earnings_disable_the_earnings_methods(pe):
    c = comps(pe=pe)
    assert c["graham_number"] is None and c["fair_pe"] is None and c["vs_history"] is None
    assert c["price_sales"] is not None  # sales-based still applies
    assert opportunity(c) is not None


def test_negative_equity_disables_graham_number():
    assert comps(pb=-2.0)["graham_number"] is None
    assert comps(pb=None)["graham_number"] is None


def test_expensive_stock_has_negative_margin():
    assert comps(pe=30.0)["fair_pe"] == pytest.approx(-1.0)


def test_opportunity_is_median_of_applicable_components():
    assert opportunity({"a": 0.1, "b": 0.5, "c": None}) == pytest.approx(0.3)
    assert opportunity({"a": 0.1, "b": 0.5, "c": 0.9}) == pytest.approx(0.5)
    assert opportunity({"a": None}) is None and opportunity({}) is None


def test_candidate_thresholds_are_inclusive_and_need_both():
    assert is_candidate(0.7, 0.2) and not is_candidate(0.69, 0.5) and not is_candidate(0.9, 0.19)
    assert not is_candidate(None, 0.5) and not is_candidate(0.9, None)


def test_every_criterion_has_a_plain_hebrew_meaning():
    from value_scanner.analysis.gurus import buffett, fisher, graham, neff, piotroski, screen
    from value_scanner.analysis.meanings import MEANINGS, meaning

    modules = (screen, graham, fisher, piotroski, buffett, neff)
    ids = {(c.guru, cid) for m in modules for cid, c in m.CRITERIA.items()}
    assert ids == set(MEANINGS)  # none missing, none left over for a removed criterion
    assert all(meaning(g, c).strip().endswith(".") for g, c in ids)
    assert meaning("nope", "nope") == ""


def test_every_statement_line_seen_in_the_data_has_an_explanation():
    from pathlib import Path

    from value_scanner.learn import STATEMENT_ITEMS, explain

    text = Path("tests/fixtures/statement_items.txt").read_text(encoding="utf-8")
    seen = [line.split("\t") for line in text.splitlines()]
    assert len(seen) > 200
    assert [s for s in seen if explain(*s) is None] == []  # a new site label needs a new entry
    for statement, items in STATEMENT_ITEMS.items():
        for item, entry in items.items():
            assert entry[0].strip() and entry[1].strip().endswith("."), (statement, item)
