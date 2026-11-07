import pytest

from value_scanner.analysis.classify import classify


@pytest.mark.parametrize(
    ("sector", "industry", "labels"),
    [
        ("Technology", "Semiconductors", {"tech"}),  # semis: tech, not cyclical (doubt 3)
        ("Technology", "Software - Application", {"tech"}),
        ("Communication Services", "Electronic Gaming & Multimedia", {"tech"}),
        ("Communication Services", "Telecom Services", set()),  # doubt 8
        ("Healthcare", "Health Information Services", {"tech"}),  # VEEV, DOCS
        ("Healthcare", "Medical Instruments & Supplies", {"pharma"}),  # the teacher, 2026-11-07
        ("Healthcare", "Medical Devices", {"pharma"}),
        ("Healthcare", "Diagnostics & Research", set()),  # not a device: regular
        ("Healthcare", "Biotechnology", {"pharma"}),
        ("Healthcare", "Drug Manufacturers - General", {"pharma"}),
        ("Financials", "Banks - Regional", {"financial"}),  # K1: not cyclical
        ("Financial Services", "Asset Management", {"financial"}),
        ("Industrials", "Specialty Industrial Machinery", set()),  # doubt 4: regular
        ("Industrials", "Engineering & Construction", {"cyclical"}),
        ("Industrials", "Airlines", {"cyclical"}),
        ("Consumer Discretionary", "Footwear & Accessories", {"cyclical"}),  # doubt 5
        ("Consumer Discretionary", "Residential Construction", {"cyclical"}),
        ("Consumer Staples", "Beverages - Non-Alcoholic", set()),  # doubt 7: regular
        ("Utilities", "Utilities - Regulated Electric", set()),
        ("Energy", "Oil & Gas E&P", {"cyclical"}),
        ("Materials", "Gold", {"cyclical"}),
        ("Real Estate", "REIT - Industrial", {"cyclical"}),
        (None, None, set()),
        ("", "", set()),
    ],
)
def test_labels(sector, industry, labels):
    assert set(classify(sector, industry).labels) == labels


def test_derived_parameters():
    tech = classify("Technology", "Software - Application")
    assert (tech.pe_limit, tech.rd_applies, tech.cyclical, tech.net_margin_limit) == (
        25.0,
        True,
        False,
        15.0,
    )
    pharma = classify("Healthcare", "Biotechnology")
    assert (pharma.pe_limit, pharma.rd_applies, pharma.net_margin_limit) == (25.0, True, 15.0)
    device = classify("Healthcare", "Medical Devices")  # devices count as pharma
    assert (device.pe_limit, device.rd_applies, device.net_margin_limit) == (25.0, True, 15.0)
    bank = classify("Financials", "Banks - Regional")
    assert (bank.pe_limit, bank.rd_applies, bank.net_margin_limit, bank.cyclical) == (
        15.0,
        False,
        8.0,
        False,
    )
    cyc = classify("Energy", "Oil & Gas E&P")
    assert (cyc.pe_limit, cyc.cyclical, cyc.rd_applies, cyc.net_margin_limit) == (
        15.0,
        True,
        False,
        8.0,
    )
    plain = classify("Consumer Staples", "Packaged Foods")
    assert (plain.pe_limit, plain.cyclical, plain.labels) == (15.0, False, {})


def test_every_label_has_a_reason():
    assert classify("Energy", "Oil & Gas E&P").labels == {"cyclical": "sector: Energy"}
