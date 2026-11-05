"""Synthetic data for tests. No real scraped data is committed (public repo)."""

from __future__ import annotations

# A stock that passes all 8 lesson-3 filters with room to spare.
PASSING = {
    "marketCap": 5e9,
    "peRatio": 15.0,
    "revenueGrowth5Y": 10.0,
    "profitMargin": 12.0,
    "epsGrowth5Y": 8.0,
    "debtEquity": 0.2,
    "currentRatio": 2.5,
    "roe5y": 15.0,
}


def point(**overrides):
    """Data-point dict for one stock: PASSING values plus extras, with overrides."""
    base = {
        **PASSING,
        "country": "United States",
        "sector": "Industrials",
        "industry": "Machinery",
        "exchange": "NASDAQ",
        "price": 50.0,
        "priceDate": "2026-11-05",
        "psRatio": 2.0,
        "pbRatio": 3.0,
        "pOcfRatio": 10.0,
        "peRatio5Y": 18.0,
        "lastEarningsDate": "2026-08-01",
        "nextEarningsDate": "2026-11-20",
    }
    base.update(overrides)
    return base


def screener_json(stocks: dict[str, dict]):
    """Build the (initial, data_points) responses from {symbol: {name?, volume?, **points}}."""
    rows, points = [], {}
    for symbol, spec in stocks.items():
        spec = dict(spec)
        name = spec.pop("name", f"{symbol} Corp")
        volume = spec.pop("volume", 1000)
        rows.append([symbol, name, 1.0, 1.0, 0.0, "x", volume, 10.0])
        points[symbol] = point(**spec)
    initial = {
        "status": 200,
        "data": {
            "count": len(rows),
            "columns": ["s", "n", "marketCap", "price", "change", "industry", "volume", "peRatio"],
            "rows": rows,
        },
    }
    return initial, {"status": 200, "data": {"data": points}}
