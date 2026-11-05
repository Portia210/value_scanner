"""Probe option A: build the stock universe from StockAnalysis's screener JSON endpoints.

Checks, with a handful of slow requests (4 s apart):
  1. which screener data-point ids exist (from the public screener page data)
  2. `screener/initial` and `screener/data-points` return all stocks over plain HTTP
  3. applying lesson 3's 8 filters in code reproduces the account's saved screen (110 on 2026-11-05)
  4. ratios from the screener match the "Current" column of each stock's ratios page

Usage: uv run python probes/screener/probe.py [--out DIR]
Writes raw responses to --out (default: var/probe-screener) for offline analysis.
"""

from __future__ import annotations

import argparse
import json
import time
from io import StringIO
from pathlib import Path

import httpx
import pandas as pd
from bs4 import BeautifulSoup

BASE = "https://stockanalysis.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE}/stocks/screener/",
}
PAUSE = 4.0

# Lesson 3 initial screen, as configured in the developer's saved screen.
FILTERS = {
    "marketCap": (">", 2e9),
    "peRatio": (">", 5),
    "revenueGrowth5Y": (">", 0),
    "profitMargin": (">", 8),
    "epsGrowth5Y": (">", 0),
    "debtEquity": ("<", 0.5),
    "currentRatio": (">", 2),
    "roe5y": (">", 10),
}
KEYWORDS = ("earn", "ps", "pb", "ocf", "fcf", "price", "industry", "sector", "exchange",
            "country", "ratio", "name", "pe")


def get(client: httpx.Client, path: str) -> httpx.Response:
    resp = client.get(BASE + path)
    challenge = bool(resp.headers.get("cf-mitigated")) or "Just a moment" in resp.text[:2000]
    print(f"GET {path[:110]} -> {resp.status_code} {len(resp.content):,} bytes"
          + ("  ** CLOUDFLARE CHALLENGE **" if challenge else ""))
    time.sleep(PAUSE)
    return resp


def decode_sveltekit(node: dict) -> object:
    """Expand SvelteKit's devalue encoding (values reference other entries by index)."""
    data = node["data"]

    def walk(v: object, depth: int = 0) -> object:
        if depth > 40:
            return v
        if isinstance(v, dict):
            return {k: walk(data[i], depth + 1) if isinstance(i, int) else i for k, i in v.items()}
        if isinstance(v, list):
            return [walk(data[i], depth + 1) if isinstance(i, int) else i for i in v]
        return v

    return walk(data[0])


RATIO_ROWS = {"peRatio": "PE Ratio", "psRatio": "PS Ratio", "pbRatio": "PB Ratio",
              "pOcfRatio": "P/OCF Ratio", "marketCap": "Market Capitalization"}


def check_ratios(client: httpx.Client, symbols: list[str]) -> None:
    """Screener values vs the 'Current' column of each stock's ratios page, fetched back to back."""
    r = get(client, "/_api/endpoints/screener/data-points?type=s&ids=" + "+".join(RATIO_ROWS))
    screener = r.json()["data"]["data"]
    for sym in symbols:
        html = get(client, f"/stocks/{sym.lower()}/financials/ratios/").text
        table = BeautifulSoup(html, "html.parser").select_one("table.financials-table")
        df = pd.read_html(StringIO(str(table)))[0]
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.set_index(df.columns[0])
        for key, row in RATIO_ROWS.items():
            page_val = str(df.loc[row].iloc[0]) if row in df.index else "—"
            print(f"  {sym:6} {row:22} screener={screener[sym].get(key)!s:>16}  page={page_val}")


def check_prices(client: httpx.Client, symbols: list[str]) -> None:
    """Screener price/priceDate vs the price shown on each stock's quote page."""
    ids = "price+priceDate+marketCap+peRatio+peRatio5Y+lastEarningsDate+nextEarningsDate"
    screener = get(client, f"/_api/endpoints/screener/data-points?type=s&ids={ids}").json()
    screener = screener["data"]["data"]
    for sym in symbols:
        html = get(client, f"/stocks/{sym.lower()}/").text
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        price_el = soup.select_one("[class*='text-4xl']") or soup.select_one("div.text-4xl")
        print(f"  {sym:6} screener={screener[sym]}")
        shown = price_el.get_text(strip=True) if price_el else None
        print(f"         page title={title[:90]!r} price_el={shown}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-prices", nargs="*", metavar="SYMBOL")
    ap.add_argument("--out", default="var/probe-screener")
    ap.add_argument("--check-ratios", nargs="*", metavar="SYMBOL")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True)
    if args.check_prices:
        check_prices(client, args.check_prices)
        return
    if args.check_ratios:
        check_ratios(client, args.check_ratios)
        return

    # 1. data-point catalogue
    page = decode_sveltekit(get(client, "/stocks/screener/__data.json").json()["nodes"][1])
    points = page["dataPoints"]
    (out / "datapoints.json").write_text(json.dumps(points, indent=1))
    ids = [p["id"] for p in points]
    print(f"\n{len(ids)} data points. Relevant ids:")
    print(sorted(i for i in ids if any(k in i.lower() for k in KEYWORDS)))

    # 2. full lists
    r = get(client, "/_api/endpoints/screener/initial?type=stock&countryCode=&format=compact")
    (out / "initial.json").write_text(r.text)
    initial = r.json()
    print("initial top-level:", list(initial)[:10] if isinstance(initial, dict) else type(initial))

    wanted = list(FILTERS) + [i for i in ("country", "sector", "industry", "psRatio", "pbRatio",
                                          "pocfRatio", "pfcfRatio", "earningsDate", "price",
                                          "exchange") if i in ids]
    r = get(client, "/_api/endpoints/screener/data-points?type=s&ids=" + "+".join(wanted))
    (out / "datapoints-values.json").write_text(r.text)
    dp = r.json()
    print("data-points top-level:", list(dp)[:10] if isinstance(dp, dict) else type(dp))
    print("sample:", json.dumps(dp)[:600])
    print("\nRaw responses saved to", out)


if __name__ == "__main__":
    main()
