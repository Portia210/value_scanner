"""Cyclical vs Defensive stock classifier using weighted scoring and AI fallback."""

import os
import json
import pandas as pd
from typing import Dict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import EXISTING_STOCKS_FILE_PATH
from utils.get_symbol_csvs_paths import get_symbol_csvs_paths
from utils.pd_helpers import get_row_safe
from enums import IncomeIndex
from utils.logger import get_logger

load_dotenv()
logger = get_logger()


def _sector_score(sector: str, industry: str) -> int:
    """Calculate sector-based score (0-40 points)."""
    if not sector:
        return 20  # Default for unknown

    # Cyclical sectors
    CYCLICAL_SECTORS = {'Materials', 'Consumer Discretionary', 'Financials', 'Real Estate', 'Energy'}
    if sector in CYCLICAL_SECTORS:
        return 40

    # Tech with semiconductors
    if sector == 'Technology' and industry and 'Semiconductor' in industry:
        return 30

    # Defensive sectors
    DEFENSIVE_SECTORS = {'Consumer Staples', 'Utilities', 'Healthcare'}
    if sector in DEFENSIVE_SECTORS:
        return 0

    # All others
    return 20


def _beta_score(beta: float) -> int:
    """Calculate beta-based score (0-30 points)."""
    if beta is None:
        return 10  # Default mid-range

    if beta > 1.3:
        return 30
    elif beta > 1.0:
        return 20
    elif beta >= 0.8:
        return 10
    else:
        return 0


def _volatility_score(income_df: pd.DataFrame, last_5_years: list) -> int:
    """Calculate financial volatility score (0-30 points)."""
    if income_df is None or not last_5_years or len(last_5_years) < 3:
        return 0

    score = 0

    # Margin volatility (15 pts)
    margins_row = get_row_safe(income_df, IncomeIndex.OPERATING_MARGIN_PERCENT, last_5_years)
    if margins_row is not None:
        margins = margins_row.dropna()
        if len(margins) >= 3:
            margin_spread = margins.max() - margins.min()
            if margin_spread > 10:  # Spread > 10%
                score += 15

    # Revenue instability (15 pts)
    revenue_row = get_row_safe(income_df, IncomeIndex.REVENUE, last_5_years)
    if revenue_row is not None:
        revenues = revenue_row.dropna()
        if len(revenues) >= 2:
            # Calculate YoY growth for each consecutive year
            for i in range(len(revenues) - 1):
                current_rev = revenues.iloc[i]
                prev_rev = revenues.iloc[i + 1]
                if prev_rev > 0:
                    yoy_growth = (current_rev - prev_rev) / prev_rev
                    if yoy_growth < -0.05:  # Drop > 5%
                        score += 15
                        break

    return score


def calculate_cyclical_score(symbol: str) -> dict:
    """Calculate cyclical score (0-100) for a stock symbol."""
    # Load company info
    try:
        with open(EXISTING_STOCKS_FILE_PATH) as f:
            companies = json.load(f)

        if symbol not in companies:
            logger.warning(f"Symbol {symbol} not found in companies")
            return {"score": None, "classification": "Unknown", "breakdown": {}}

        company = companies[symbol]
        sector = company.get('sector')
        industry = company.get('industry')
        beta = company.get('beta')

    except Exception as e:
        logger.error(f"Error loading company data for {symbol}: {e}")
        return {"score": None, "classification": "Unknown", "breakdown": {}}

    # Load income data
    income_df = None
    last_5_years = []
    try:
        paths = get_symbol_csvs_paths(symbol)
        if paths and paths.get('income'):
            income_df = pd.read_csv(paths['income'], index_col=0)
            # Get last 5 fiscal years (exclude TTM if present)
            fy_cols = [col for col in income_df.columns if col.startswith('FY')]
            last_5_years = fy_cols[:5] if len(fy_cols) >= 5 else fy_cols
    except Exception as e:
        logger.warning(f"Error loading income data for {symbol}: {e}")

    # Calculate scores
    sector_pts = _sector_score(sector, industry)
    beta_pts = _beta_score(beta)
    volatility_pts = _volatility_score(income_df, last_5_years)

    total_score = sector_pts + beta_pts + volatility_pts

    # Determine classification
    if total_score >= 61:
        classification = "Cyclical"
    elif total_score <= 40:
        classification = "Defensive"
    else:
        classification = "Gray Zone"  # Needs AI

    return {
        "score": total_score,
        "classification": classification,
        "breakdown": {
            "sector_score": sector_pts,
            "beta_score": beta_pts,
            "volatility_score": volatility_pts,
            "sector": sector,
            "industry": industry,
            "beta": beta
        }
    }


async def ask_ai_classifier_batch(companies: List[dict]) -> Dict[str, dict]:
    """Classify gray-zone companies using OpenAI GPT-3.5 Turbo (batch of up to 5)."""
    if not companies or len(companies) == 0:
        return {}

    # Load API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        # Default to Defensive for gray zone if no API key
        return {
            company['symbol']: {
                'classification': 'Defensive',
                'explanation': 'Default classification (no API key available)'
            } for company in companies
        }

    try:
        # Initialize OpenAI GPT-3.5 Turbo
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=api_key,
            temperature=0.1,
            max_retries=2
        )

        # Build prompt with all companies
        companies_text = "\n".join([
            f"{i+1}. {c['symbol']}: Sector={c['sector']}, Industry={c['industry']}, Beta={c.get('beta', 'N/A')}"
            for i, c in enumerate(companies)
        ])

        system_msg = SystemMessage(content="""You are a financial analyst expert in classifying stocks as Cyclical or Defensive.

Cyclical stocks: Performance tied to economic cycles (e.g., tech, consumer discretionary, industrials, materials).
Defensive stocks: Stable performance regardless of economy (e.g., utilities, consumer staples, healthcare).

Analyze each company and return ONLY valid JSON in this format:
{
  "SYMBOL1": {
    "classification": "Cyclical",
    "explanation": "Brief 1-2 sentence explanation"
  },
  "SYMBOL2": {
    "classification": "Defensive",
    "explanation": "Brief 1-2 sentence explanation"
  }
}

Keep explanations concise and focus on key factors.""")

        human_msg = HumanMessage(content=f"""Classify these companies as "Cyclical" or "Defensive" with explanations:

{companies_text}

Return JSON only.""")

        # Get AI response
        response = llm.invoke([system_msg, human_msg])

        # Parse JSON response
        result_text = response.content.strip()
        # Remove markdown code blocks if present
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()

        classifications = json.loads(result_text)

        logger.info(f"AI classified {len(classifications)} companies")
        return classifications

    except Exception as e:
        logger.error(f"Error in AI classification: {e}")
        # Default to Defensive for gray zone on error
        return {
            company['symbol']: {
                'classification': 'Defensive',
                'explanation': 'Default classification due to AI error'
            } for company in companies
        }


async def classify_companies_batch(symbols: List[str]) -> Dict[str, dict]:
    """Classify multiple companies, batching AI requests for gray-zone cases."""
    results = {}
    gray_zone_companies = []

    # First pass: Calculate scores for all companies
    for symbol in symbols:
        score_result = calculate_cyclical_score(symbol)
        results[symbol] = score_result

        # Collect gray-zone companies for AI batch
        if score_result['classification'] == 'Gray Zone':
            gray_zone_companies.append({
                'symbol': symbol,
                'sector': score_result['breakdown'].get('sector'),
                'industry': score_result['breakdown'].get('industry'),
                'beta': score_result['breakdown'].get('beta')
            })

    # Second pass: Process gray-zone companies with AI (batch of 5)
    if gray_zone_companies:
        # Process in batches of 5
        for i in range(0, len(gray_zone_companies), 5):
            batch = gray_zone_companies[i:i+5]
            ai_classifications = await ask_ai_classifier_batch(batch)

            # Update results with AI classifications and explanations
            for symbol, ai_result in ai_classifications.items():
                if symbol in results:
                    if isinstance(ai_result, dict):
                        results[symbol]['classification'] = ai_result.get('classification', 'Defensive')
                        results[symbol]['ai_explanation'] = ai_result.get('explanation', '')
                    else:
                        # Fallback for old format
                        results[symbol]['classification'] = ai_result
                        results[symbol]['ai_explanation'] = 'No explanation provided'
                    results[symbol]['ai_decision'] = True

    return results
