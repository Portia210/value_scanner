"""SEC EDGAR: find a company's latest annual report and cut out the chapters we summarise (E7).

10-K: Item 1 (Business), Item 1A (Risk Factors, optional), Item 7 (MD&A).
20-F: Item 4 (Information on the Company), Item 3.D (Risk Factors, optional), Item 5 (Operating
and Financial Review). Other annual forms (40-F, ...) are reported as unsupported.

The SEC asks every automated client to identify itself with a contact address, so requests carry
`MY_EMAIL` in the User-Agent (decision D16); it is never logged. Requests are slow (>= 1 s apart,
the SEC allows 10 per second) and bounded.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
ANNUAL_FORMS = ("10-K", "20-F")
MIN_GAP_SECONDS = 1.0

# Minimum length (characters) of a required chapter; a shorter one means the cut went wrong.
MIN_CHARS = {"10-K": {"1": 5000, "7": 3000}, "20-F": {"4": 5000, "5": 3000}}
# Chapters sent to the model, in order: (key, label, required)
CHAPTERS = {
    "10-K": [
        ("1", "Item 1. Business", True),
        ("1A", "Item 1A. Risk Factors", False),
        ("7", "Item 7. MD&A", True),
    ],
    "20-F": [
        ("4", "Item 4. Information on the Company", True),
        ("3D", "Item 3.D Risk Factors", False),
        ("5", "Item 5. Operating and Financial Review", True),
    ],
}
MAX_CHAPTER_CHARS = 120_000  # a risk-factors chapter can be enormous; keep the head


class SecError(RuntimeError):
    """The SEC could not be reached or answered with something unusable."""


class ExtractionFailed(SecError):
    """The report was found but a required chapter could not be cut out (alert-worthy)."""


class Unsupported(SecError):
    """The company has no 10-K or 20-F (for example a 40-F filer)."""


@dataclass(frozen=True)
class Filing:
    cik: int
    form: str
    accession: str  # with dashes, e.g. 0000824142-26-000005
    filing_date: str
    primary_document: str
    sic_description: str | None

    @property
    def url(self) -> str:
        return ARCHIVE_URL.format(
            cik=self.cik, accession=self.accession.replace("-", ""), document=self.primary_document
        )


class SecClient:
    def __init__(
        self,
        contact: str,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        headers = {"User-Agent": f"value-scanner {contact}", "Accept-Encoding": "gzip, deflate"}
        self._client = client or httpx.Client(headers=headers, timeout=60, follow_redirects=True)
        self._sleep = sleep
        self._last = 0.0
        self._tickers: dict[str, int] | None = None

    def _get(self, url: str) -> httpx.Response:
        wait = MIN_GAP_SECONDS - (time.monotonic() - self._last)
        if wait > 0:
            self._sleep(wait)
        self._last = time.monotonic()
        try:
            resp = self._client.get(url)
        except httpx.HTTPError as exc:
            raise SecError(f"network error: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise SecError(f"SEC answered HTTP {resp.status_code} for {url.split('/')[2]}")
        return resp

    def cik(self, symbol: str) -> int:
        if self._tickers is None:
            data = self._get(TICKERS_URL).json()
            self._tickers = {v["ticker"].upper(): int(v["cik_str"]) for v in data.values()}
        # StockAnalysis writes share classes "BRK.B"; the SEC list writes "BRK-B"
        for candidate in (symbol.upper(), symbol.upper().replace(".", "-")):
            if candidate in self._tickers:
                return self._tickers[candidate]
        raise Unsupported(f"{symbol} is not in the SEC ticker list")

    def latest_annual_filing(self, symbol: str) -> Filing:
        cik = self.cik(symbol)
        data = self._get(SUBMISSIONS_URL.format(cik=cik)).json()
        recent = data["filings"]["recent"]
        for form, accession, date, document in zip(
            recent["form"],
            recent["accessionNumber"],
            recent["filingDate"],
            recent["primaryDocument"],
            strict=True,
        ):
            if form in ANNUAL_FORMS:  # the list is newest first
                return Filing(cik, form, accession, date, document, data.get("sicDescription"))
        raise Unsupported(f"{symbol} has no 10-K or 20-F among its recent filings")

    def download_text(self, filing: Filing) -> str:
        return html_to_text(self._get(filing.url).text)

    def extract_from(self, filing: Filing) -> list[tuple[str, str]]:
        """Download the report and cut out its chapters (ExtractionFailed if a required one is
        missing)."""
        return extract_chapters(self.download_text(filing), filing.form)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = text.replace("\xa0", " ")
    lines = (re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


_HEADING = re.compile(r"^item\s+(\d{1,2}[A-C]?)\s*[\.\:\-–—]?\s*(.{0,120})$", re.IGNORECASE)


def _headings(text: str) -> list[tuple[int, str]]:
    """(character offset, item key) of every line that looks like an 'Item N.' heading.
    A heading may be split over two lines ('Item 1.' / 'Business') - both are accepted."""
    out, pos = [], 0
    for line in text.split("\n"):
        m = _HEADING.match(line.strip())
        if m and len(line) < 140:
            out.append((pos, m.group(1).upper()))
        pos += len(line) + 1
    return out


def extract_chapter(text: str, item: str) -> str:
    """The longest stretch that starts at an 'Item <item>' heading and ends at the next heading
    of a different item. Taking the longest skips the table of contents (a short stretch)."""
    heads = _headings(text)
    best = ""
    for i, (start, key) in enumerate(heads):
        if key != item:
            continue
        end = next((p for p, k in heads[i + 1 :] if k != item), len(text))
        if end - start > len(best):
            best = text[start:end]
    return best


def _risk_factors_20f(text: str) -> str:
    item3 = extract_chapter(text, "3")
    m = re.search(r"^\s*D\.\s*Risk Factors", item3, re.IGNORECASE | re.MULTILINE)
    return item3[m.start() :] if m else ""


def extract_chapters(text: str, form: str) -> list[tuple[str, str]]:
    """[(label, text)] of the chapters to summarise, or ExtractionFailed when a required one is
    missing or implausibly short."""
    if form not in CHAPTERS:
        raise Unsupported(f"form {form} is not supported")
    result = []
    for key, label, required in CHAPTERS[form]:
        body = _risk_factors_20f(text) if key == "3D" else extract_chapter(text, key)
        if required and len(body) < MIN_CHARS[form][key]:
            raise ExtractionFailed(f"{label}: found {len(body)} characters")
        if body:
            result.append((label, body[:MAX_CHAPTER_CHARS]))
    return result
