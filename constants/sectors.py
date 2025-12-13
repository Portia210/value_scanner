"""
Centralized definitions for Sectors and Industries used in classification.
"""

# Sectors that are explicitly Technology or Communication Services
TECH_SECTORS = {
    'Technology',
    'Communication Services'
}

# Industries related to Biotech and Pharma
PHARMA_INDUSTRIES = {
    'Biotechnology',
    'Drug Manufacturers - General',
    'Drug Manufacturers - Specialty & Generic',
    'Health Information Services', # Often SaaS-like
    'Medical Instruments & Supplies', # Often Tech-like
    'Life Sciences Tools & Services',
}

# Sectors generally considered Cyclical
CYCLICAL_SECTORS = {
    'Energy',
    'Materials',
    'Industrials',
    'Financials',
    'Consumer Discretionary',
    'Real Estate',
    # GICS / Data Provider Variations
    'Basic Materials',
    'Consumer Cyclical',
    'Financial Services',
}

# Specific Industries considered Cyclical (if sector is ambiguous or for strict checks)
CYCLICAL_INDUSTRIES = {
    # Auto
    'Auto Manufacturers', 'Auto Parts', 'Recreational Vehicles',
    # Transport
    'Airlines', 'Trucking', 'Railroads', 'Marine Shipping',
    # Travel/Leisure
    'Resorts & Casinos', 'Lodging', 'Travel Services', 'Restaurants', 
    'Leisure', 'Gambling',
    # Semi (Also Tech, but cyclical behavior)
    'Semiconductors', 'Semiconductor Equipment & Materials', 'Electronic Components',
    # Commodities / Heavy Industry
    'Steel', 'Aluminum', 'Copper', 'Gold', 'Silver', 'Other Industrial Metals & Mining',
    'Chemicals', 'Agricultural Inputs', 'Building Materials',
    # Construction
    'Residential Construction', 'Engineering & Construction',
    # Banks/Finance
    'Banks', 'Banks - Regional', 'Asset Management', 'Capital Markets',
}

# Sectors considered Defensive (Gravity applies)
DEFENSIVE_SECTORS = {
    'Utilities',
    'Consumer Staples',
    'Financials', # Banks/Insurance often defensive-ish unless crisis
    # GICS / Data Provider Variations
    'Cons. Staples',
}
