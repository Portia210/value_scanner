import os
import random
import asyncio
import httpx
from bs4 import BeautifulSoup
from utils.pd_helpers import parse_html_table_str
from utils.df_cleaner import full_df_cleaning
from utils.logger import get_logger
from playwright_utils.cookie_utils import load_cookies_from_file

logger = get_logger()

class HttpReportsFetcher:
    REPORTS_ROUTES = {
        "income": "/financials/",
        "balance-sheet": "/financials/balance-sheet/",
        "cash-flow": "/financials/cash-flow-statement/",
        "ratios": "/financials/ratios/",
    }

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._load_cookies()
        self._rate_limit_saved = False
        self._request_counter = 0
        self._breather_lock = asyncio.Lock()

    def _load_cookies(self):
        cookies_list = load_cookies_from_file("cookies.txt", domain="stockanalysis.com")
        for cookie in cookies_list:
             self.client.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', 'stockanalysis.com'))
        
        # Manually set headers mimicking the user's curl command (shortened for brevity but retaining critical ones)
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Priority': 'u=0, i'
        })
    
    async def fetch_all_reports(self, symbol: str, stock_href: str):
        """Fetch all reports for a given symbol sequentially with delays, ensuring completion."""
        logger.debug(f"Fetching financial data for: {symbol}")
        base_url = f"https://stockanalysis.com{stock_href}"
        
        for report_type, url_suffix in self.REPORTS_ROUTES.items():
            target_file = f"data/{symbol}/{report_type}.csv"
            
            # Resume capability: skip if already exists
            if os.path.exists(target_file):
                continue
            
            # Integrity loop: keep trying this specific report until we get it
            while True:
                # Construct URL properly
                if report_type == "income":
                     url = base_url + "financials/" # Special case for main financials page
                else:
                     url = base_url + url_suffix.replace("/financials/", "financials/")

                await self._fetch_single_report(symbol, url, report_type, target_file)
                
                if os.path.exists(target_file):
                    # Success, wait before next report
                    await asyncio.sleep(random.uniform(0.8, 1))
                    break
                else:
                    # Failed to download, wait longer before retrying to avoid hammering
                    logger.warning(f"Failed to verify {report_type} for {symbol}, retrying in 20s...")
                    await asyncio.sleep(20)
        
        logger.info(f"Finished fetching all reports for {symbol}")


    def is_report_missing(self, symbol: str) -> bool:
        if not os.path.exists(f"data/{symbol}"):
            return True
        for report in self.REPORTS_ROUTES.keys():
            if not os.path.exists(f"data/{symbol}/{report}.csv"):
                return True
        return False

    async def _fetch_single_report(self, symbol: str, url: str, report_type: str, target_file: str):
        
        for attempt in range(3):
            # Smart Sleep: Take a breather every 10 requests
            # Use lock to ensure ALL workers wait when one triggers the breather
            async with self._breather_lock:
                self._request_counter += 1
                if self._request_counter % 10 == 0:
                    logger.info(f"Made {self._request_counter} requests. Taking a 15s breather to respect rate limits...")
                    await asyncio.sleep(15)

            try:
                response = await self.client.get(url, follow_redirects=True)
                
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "unknown")
                    rate_limit = response.headers.get("X-RateLimit-Limit", "unknown")
                    rate_remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
                    
                    # Aggressive backoff on 429: server is angry, hide for a minute
                    logger.warning(f"Rate limit hit for {symbol} - {report_type}. Retry-After: {retry_after}. Sleeping for 60s...")
                    
                    if not self._rate_limit_saved:
                        try:
                            with open("rate_limit_debug.txt", "w") as f:
                                f.write(f"URL: {url}\n")
                                f.write("HEADERS:\n")
                                for k, v in response.headers.items():
                                    f.write(f"{k}: {v}\n")
                                f.write("\nBODY:\n")
                                f.write(response.text)
                            logger.info("Saved first rate limit response to rate_limit_debug.txt")
                            self._rate_limit_saved = True
                        except Exception as e:
                            logger.error(f"Failed to save rate limit debug info: {e}")

                    await asyncio.sleep(60)
                    continue
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch {url}: Status {response.status_code}")
                    return

                html_content = response.text
                
                soup = BeautifulSoup(html_content, 'html.parser')
                table = soup.select_one("table.financials-table")
                
                if not table:
                    logger.error(f"No financials table found for {symbol} - {report_type}")
                    if "Access Denied" in html_content or "Just a moment" in html_content:
                         logger.critical("Access Denied/WAF block detected.")
                         await asyncio.sleep(60) # Long sleep
                    return

                table_inner_html = "".join([str(x) for x in table.contents])
                
                df = parse_html_table_str(table_inner_html)
                df = full_df_cleaning(df)
                
                os.makedirs(f"data/{symbol}", exist_ok=True)
                df.to_csv(target_file)
                logger.debug(f"Saved {report_type} for {symbol}")
                return

            except httpx.RequestError as e:
                logger.error(f"Request error for {symbol}: {e}")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Unexpected error parsing {symbol} {report_type}: {e}")
                return
