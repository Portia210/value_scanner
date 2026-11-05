import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "compare_v1_v2", Path(__file__).parents[1] / "tools" / "compare_v1_v2.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REPORT = """# AAA

> **Basic Reports Check**
- current ratio (≥ 2): 🟢 **PASS**, Current Ratio value (2.79). value greater than 2.00.
- ROE (avg ≥ 15%):  🔴 **FAIL**, avarage: 12.97, total: 64.86
- **Classification Used**: Cyclical

> **Benjamin Graham Check** (AAA - Industrials - Cyclical)
- graham number (P/E × P/B < 22): N/A (Tech company - uses P/OCF check instead)
- P/E ratio (5-25): 🔴 **FAIL**, PE Ratio value (56.75) should be between 5 and 25

> **Ken Fisher Super Stocks Check**
- Innovation Factor: 🔴 **FAIL**, 🔴 MISSING R&D DATA
"""


def test_parse_v1_report_sections_labels_and_statuses():
    got = mod.parse_v1_report(REPORT)
    assert got[("Basic", "current ratio")][0] == "PASS"
    assert got[("Basic", "ROE")][0] == "FAIL"
    assert got[("Graham", "graham number")][0] == "NA"
    assert got[("Graham", "P/E ratio")][0] == "FAIL"
    assert got[("Fisher", "Innovation Factor")][0] == "FAIL"
    assert not any("Classification" in k[1] for k in got)


def test_every_mapped_check_points_at_a_real_v2_criterion():
    from value_scanner.analysis.docs import GURUS

    for guru, cid, _ in mod.MAP.values():
        assert cid in GURUS[guru][1], (guru, cid)
