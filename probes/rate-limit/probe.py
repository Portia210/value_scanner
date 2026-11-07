"""Probe (R6): how fast can statement pages be fetched from this IP before Cloudflare objects?

Ramps the request rate up in phases (default: 3-6 s -> back-to-back, then 2 workers), each phase on
fresh symbols (so edge-cache hits don't hide the limit). STOPS THE WHOLE RAMP AT THE FIRST
challenge/429 - no retry, no bypass. Then it measures how long the block lasts with one request at
growing intervals. Prints JSON lines; per-request lines only for non-ok and every 10th request.

Env: PHASES = JSON [[name, workers, lo_s, hi_s, n], ...] to override the ramp; H2=1 for HTTP/2;
PAGE = path under /stocks/<sym>/ (default the HTML income statement; use
financials/income-statement/__data.json for the JSON variant); RECOVERY=0 skips the recovery
measurement; ALT=0 skips the alternate-endpoint check.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import statistics
import time

import httpx
from bs4 import BeautifulSoup

BASE = "https://stockanalysis.com"
INITIAL = BASE + "/_api/endpoints/screener/initial?type=stock&countryCode=&format=compact"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
PAGE = os.environ.get("PAGE", "financials/income-statement/")
DEFAULT_PHASES = [
    ["baseline 3-6s", 1, 3.0, 6.0, 30],
    ["2-4s", 1, 2.0, 4.0, 40],
    ["1-2s", 1, 1.0, 2.0, 60],
    ["0.5-1s", 1, 0.5, 1.0, 80],
    ["0.2-0.5s", 1, 0.2, 0.5, 100],
    ["back-to-back", 1, 0.0, 0.05, 100],
    ["2 workers 0.5-1s", 2, 0.5, 1.0, 100],
    ["4 workers 0.5-1s", 4, 0.5, 1.0, 120],
]
T0 = time.monotonic()


def log(**kw: object) -> None:
    print(json.dumps({"t": round(time.monotonic() - T0, 1), **kw}, ensure_ascii=False), flush=True)


def classify(resp: httpx.Response) -> str:
    if resp.headers.get("cf-mitigated") or "Just a moment" in resp.text[:2000]:
        return "challenge"
    if resp.status_code == 429:
        return "rate_limited"
    if resp.status_code != 200:
        return f"http_{resp.status_code}"
    if PAGE.endswith(".json"):
        return "ok" if '"financialData"' in resp.text else "no_table"
    return (
        "ok"
        if BeautifulSoup(resp.text, "html.parser").select_one("table.financials-table")
        else "no_table"
    )


async def get_symbols(client: httpx.AsyncClient) -> list[str]:
    resp = await client.get(INITIAL, headers={"Referer": BASE + "/stocks/screener/"})
    log(
        step="screener_json",
        status=resp.status_code,
        bytes=len(resp.content),
        cf_mitigated=resp.headers.get("cf-mitigated"),
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    cols = data["columns"]
    s, cap = cols.index("s"), cols.index("marketCap")
    rows = [r for r in data["rows"] if (r[cap] or 0) > 1e9 and "." not in r[s]]
    random.shuffle(rows)
    return [r[s].lower() for r in rows]


async def one(client: httpx.AsyncClient, symbol: str, path: str = PAGE) -> dict:
    t = time.monotonic()
    try:
        resp = await client.get(f"{BASE}/stocks/{symbol}/{path}")
    except httpx.HTTPError as exc:
        return {
            "symbol": symbol,
            "outcome": f"error_{type(exc).__name__}",
            "ms": int((time.monotonic() - t) * 1000),
        }
    return {
        "symbol": symbol,
        "outcome": classify(resp),
        "status": resp.status_code,
        "ms": int((time.monotonic() - t) * 1000),
        "bytes": len(resp.content),
        "cache": resp.headers.get("cf-cache-status"),
        "retry_after": resp.headers.get("retry-after"),
    }


async def run_phase(client, symbols: list[str], phase: list) -> tuple[dict, bool]:
    name, workers, lo, hi, n = phase
    batch = [symbols.pop() for _ in range(min(n, len(symbols)))]
    queue: asyncio.Queue[str] = asyncio.Queue()
    for s in batch:
        queue.put_nowait(s)
    stop = asyncio.Event()
    results: list[dict] = []
    started = time.monotonic()

    async def worker() -> None:
        while not stop.is_set():
            try:
                symbol = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            r = await one(client, symbol)
            results.append(r)
            if r["outcome"] != "ok" or len(results) % 10 == 0:
                log(phase=name, i=len(results), **r)
            if r["outcome"] in ("challenge", "rate_limited"):
                stop.set()
                return
            await asyncio.sleep(random.uniform(lo, hi))

    await asyncio.gather(*[worker() for _ in range(workers)])
    elapsed = time.monotonic() - started
    oks = [r for r in results if r["outcome"] == "ok"]
    ms = sorted(r["ms"] for r in oks) or [0]
    summary = {
        "phase": name,
        "workers": workers,
        "pace_s": [lo, hi],
        "requests": len(results),
        "ok": len(oks),
        "outcomes": {
            o: sum(1 for r in results if r["outcome"] == o) for o in {r["outcome"] for r in results}
        },
        "elapsed_s": round(elapsed, 1),
        "req_per_min": round(len(results) / elapsed * 60, 1) if elapsed else 0,
        "ms_median": int(statistics.median(ms)),
        "ms_p95": ms[int(len(ms) * 0.95) - 1] if len(ms) > 1 else ms[0],
        "cache": {
            c: sum(1 for r in results if r.get("cache") == c)
            for c in {r.get("cache") for r in results}
        },
        "avg_bytes": int(statistics.mean(r["bytes"] for r in oks)) if oks else 0,
    }
    log(summary=summary)
    return summary, stop.is_set()


async def alt_endpoints(client, symbol: str) -> None:
    for path in ("financials/__data.json", "financials/income-statement/__data.json"):
        t = time.monotonic()
        try:
            resp = await client.get(f"{BASE}/stocks/{symbol}/{path}")
        except httpx.HTTPError as exc:
            log(alt=path, error=type(exc).__name__)
            continue
        log(
            alt=path,
            status=resp.status_code,
            bytes=len(resp.content),
            ms=int((time.monotonic() - t) * 1000),
            ctype=resp.headers.get("content-type"),
            head=resp.text[:150].replace("\n", " "),
        )
        await asyncio.sleep(random.uniform(3, 6))


async def recovery(client, symbols: list[str]) -> None:
    """After a block: one request at growing intervals until two ok in a row (cap ~40 min)."""
    waited, good = 0, 0
    for gap in (30, 30, 60, 120, 120, 300, 300, 600, 600):
        await asyncio.sleep(gap)
        waited += gap
        r = await one(client, symbols.pop())
        log(recovery_after_s=waited, **r)
        good = good + 1 if r["outcome"] == "ok" else 0
        if good >= 2:
            log(recovered_after_s=waited)
            return
    log(recovered_after_s=None, note="still blocked after the cap")


async def main() -> None:
    phases = json.loads(os.environ["PHASES"]) if os.environ.get("PHASES") else DEFAULT_PHASES
    limits = httpx.Limits(max_connections=64, max_keepalive_connections=64)
    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=30,
        follow_redirects=True,
        limits=limits,
        http2=os.environ.get("H2") == "1",
    ) as client:
        try:
            symbols = await get_symbols(client)
        except Exception as exc:  # noqa: BLE001 - probe: report and stop
            log(fatal="screener_json", error=repr(exc)[:200])
            return
        log(step="start", symbols=len(symbols), phases=len(phases), h2=os.environ.get("H2") == "1")
        egress = await client.get("https://api.ipify.org")
        log(step="egress_ip", ip=egress.text.strip()[:45])
        await asyncio.sleep(5)
        if os.environ.get("ALT", "1") == "1":
            await alt_endpoints(client, symbols.pop())
        blocked = False
        for phase in phases:
            _, blocked = await run_phase(client, symbols, phase)
            if blocked:
                log(note="blocked - ramp stopped", at=phase[0])
                break
            await asyncio.sleep(5)
        if blocked and os.environ.get("RECOVERY", "1") == "1":
            await recovery(client, symbols)
    log(done=True)


asyncio.run(main())
