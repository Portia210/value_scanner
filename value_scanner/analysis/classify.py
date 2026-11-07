"""Company classification (C2): which pricing tests apply to which company.

Rules are the defaults of docs/classification-doubts.md (decision D6) - sector and industry
only; the old "high growth" and "volatility trap" inventions are gone. Labels:

    tech      Technology sector; software/internet/gaming in Communication Services or Healthcare
    pharma    biotechnology, drug manufacturers and medical devices (the teacher, 2026-11-07)
    financial banks, insurance, asset managers - own pricing tests, some tests not applicable
    cyclical  Energy, Materials, Real Estate, Consumer Discretionary, and cyclical industries
              (construction, building materials, ...). Tech and financial are never cyclical.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TECH_SECTORS = {"Technology", "Information Technology"}
TECH_INDUSTRIES = {"Health Information Services"}  # medical software (doubt 2)
SOFTWARE_HINTS = ("software", "internet", "gaming", "video games", "information technology")
PHARMA_INDUSTRIES = {
    "Biotechnology",
    "Drug Manufacturers - General",
    "Drug Manufacturers - Specialty & Generic",
    "Medical Devices",  # "devices count as pharma in the financial statements"
    "Medical Instruments & Supplies",
}
FINANCIAL_SECTORS = {"Financials", "Financial Services"}
CYCLICAL_SECTORS = {
    "Energy",
    "Materials",
    "Basic Materials",
    "Real Estate",
    "Consumer Discretionary",
    "Consumer Cyclical",
}
CYCLICAL_INDUSTRIES = {
    "Auto Manufacturers",
    "Auto Parts",
    "Recreational Vehicles",
    "Airlines",
    "Trucking",
    "Railroads",
    "Marine Shipping",
    "Resorts & Casinos",
    "Lodging",
    "Travel Services",
    "Restaurants",
    "Leisure",
    "Gambling",
    "Steel",
    "Aluminum",
    "Copper",
    "Gold",
    "Silver",
    "Other Industrial Metals & Mining",
    "Chemicals",
    "Agricultural Inputs",
    "Building Materials",
    "Residential Construction",
    "Engineering & Construction",
    "Building Products & Equipment",
    "Farm & Heavy Construction Machinery",
}

PE_LIMIT_DEFAULT = 15.0
PE_LIMIT_TECH = 25.0  # D5
NET_MARGIN_TECH = 15.0  # Fisher, 5-year average net margin: technology and pharma
NET_MARGIN_DEFAULT = 8.0  # ... and everyone else (the teacher, 2026-11-07)


@dataclass(frozen=True)
class Classification:
    labels: dict[str, str] = field(default_factory=dict)  # label -> reason

    @property
    def tech(self) -> bool:
        return "tech" in self.labels

    @property
    def pharma(self) -> bool:
        return "pharma" in self.labels

    @property
    def financial(self) -> bool:
        return "financial" in self.labels

    @property
    def cyclical(self) -> bool:
        return "cyclical" in self.labels

    @property
    def pe_limit(self) -> float:
        """Graham's P/E ceiling: 25 for technology and pharma, 15 otherwise."""
        return PE_LIMIT_TECH if self.tech or self.pharma else PE_LIMIT_DEFAULT

    @property
    def rd_applies(self) -> bool:
        """Fisher's market cap / R&D test is for technology and pharma only (D4)."""
        return self.tech or self.pharma

    @property
    def net_margin_limit(self) -> float:
        """Fisher's 5-year average net margin: 15% for technology and pharma, 8% otherwise."""
        return NET_MARGIN_TECH if self.tech or self.pharma else NET_MARGIN_DEFAULT


def classify(sector: str | None, industry: str | None) -> Classification:
    sector, industry = (sector or "").strip(), (industry or "").strip()
    labels: dict[str, str] = {}

    if sector in FINANCIAL_SECTORS:
        labels["financial"] = f"sector: {sector}"
    if sector in TECH_SECTORS:
        labels["tech"] = f"sector: {sector}"
    elif industry in TECH_INDUSTRIES or (
        sector not in FINANCIAL_SECTORS and any(h in industry.lower() for h in SOFTWARE_HINTS)
    ):
        labels["tech"] = f"industry: {industry}"
    if industry in PHARMA_INDUSTRIES:
        labels["pharma"] = f"industry: {industry}"

    if not labels.keys() & {"tech", "financial"}:
        if sector in CYCLICAL_SECTORS:
            labels["cyclical"] = f"sector: {sector}"
        elif industry in CYCLICAL_INDUSTRIES:
            labels["cyclical"] = f"industry: {industry}"
    return Classification(labels)
