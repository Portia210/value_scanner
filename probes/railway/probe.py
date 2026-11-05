"""Probe: does StockAnalysis serve data to this machine at the planned (slow) pace?

Runs three phases and prints one JSON line per request plus a summary:
  1. anonymous httpx — 10 stocks x 4 statement pages, 3-6 s apart (a real run segment)
  2. Playwright headless — load the screener page and log in (needs STOCK_ANALYSIS_EMAIL/PASSWORD)
  3. logged-in httpx — 3 pages with the session cookies from phase 2

Never prints credentials or cookie values. Stops a phase after 2 consecutive blocks.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import time

import httpx
from bs4 import BeautifulSoup

BASE = "https://stockanalysis.com"
STOCKS = ["aaon", "csw", "dci", "nvda", "blk", "asr", "sna", "fast", "uthr", "gntx"]
PAGES = ["financials/", "financials/balance-sheet/", "financials/cash-flow-statement/",
         "financials/ratios/"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def log(**kw: object) -> None:
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def classify(resp: httpx.Response) -> str:
    if resp.headers.get("cf-mitigated") or "Just a moment" in resp.text[:2000]:
        return "challenge"
    if resp.status_code == 429:
        return "rate_limited"
    if resp.status_code != 200:
        return f"http_{resp.status_code}"
    soup = BeautifulSoup(resp.text, "html.parser")
    return "ok" if soup.select_one("table.financials-table") else "no_table"


async def fetch_pages(client: httpx.AsyncClient, phase: str, urls: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    consecutive_blocks = 0
    for url in urls:
        t0 = time.monotonic()
        try:
            resp = await client.get(url, follow_redirects=True)
            outcome = classify(resp)
            log(phase=phase, url=url.removeprefix(BASE), status=resp.status_code, outcome=outcome,
                ms=int((time.monotonic() - t0) * 1000))
        except httpx.HTTPError as exc:
            outcome = f"error_{type(exc).__name__}"
            log(phase=phase, url=url.removeprefix(BASE), outcome=outcome)
        counts[outcome] = counts.get(outcome, 0) + 1
        blocked = outcome in ("challenge", "rate_limited")
        consecutive_blocks = consecutive_blocks + 1 if blocked else 0
        if consecutive_blocks >= 2:
            log(phase=phase, note="stopping phase after 2 consecutive blocks")
            break
        await asyncio.sleep(random.uniform(3, 6))
    return counts


async def browser_phase() -> tuple[dict[str, object], list[dict]]:
    from playwright.async_api import async_playwright

    result: dict[str, object] = {}
    cookies: list[dict] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=HEADERS["User-Agent"],
                                            viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        resp = await page.goto(f"{BASE}/stocks/screener/", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        title = await page.title()
        rows = await page.locator("#main-table tbody tr").count()
        result["screener"] = {"status": resp.status if resp else None, "title": title, "rows": rows}

        email = os.environ.get("STOCK_ANALYSIS_EMAIL")
        password = os.environ.get("STOCK_ANALYSIS_PASSWORD")
        if not (email and password):
            result["login"] = "skipped: credentials not set"
        else:
            await page.goto(f"{BASE}/login/", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            try:
                await page.fill("input#email", email)
                await page.fill("input#password", password)
                await page.click('button:has-text("Log In")')
                await page.wait_for_timeout(6000)
                cookies = await context.cookies()
                names = {c["name"] for c in cookies}
                result["login"] = {"auth_cookie": "sb-auth-auth-token" in names,
                                   "url_after": page.url.removeprefix(BASE),
                                   "title_after": await page.title()}
            except Exception as exc:  # report, don't crash the probe
                result["login"] = {"error": type(exc).__name__,
                                   "title": await page.title()}
        await browser.close()
    return result, cookies


async def main() -> None:
    started = time.time()
    log(event="start", python=sys.version.split()[0])
    summary: dict[str, object] = {}

    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        urls = [f"{BASE}/stocks/{s}/{p}" for s in STOCKS for p in PAGES]
        summary["anonymous"] = await fetch_pages(client, "anonymous", urls)

    summary["browser"], cookies = await browser_phase()

    if cookies:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            for c in cookies:
                client.cookies.set(c["name"], c["value"], domain=c["domain"])
            urls = [f"{BASE}/stocks/{s}/financials/ratios/" for s in ("aaon", "nvda", "blk")]
            summary["logged_in"] = await fetch_pages(client, "logged_in", urls)

    summary["seconds"] = int(time.time() - started)
    log(event="summary", **summary)


if __name__ == "__main__":
    asyncio.run(main())
