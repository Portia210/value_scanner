"""Company business profiles (E7): latest annual report -> chapters -> Gemini -> `profiles`.

A profile is refreshed only when a newer annual report (a new accession number) or a new prompt
version exists. A chapter that cannot be cut out is an alert ("extraction_failed"); missing
billing is an alert ("billing"). One company failing never stops the others.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from value_scanner.profile import gemini
from value_scanner.settings import Settings
from value_scanner.sources.sec import ExtractionFailed, SecClient, SecError, Unsupported
from value_scanner.storage.repo import Repository

Generate = Callable[[str, str], str]  # (api_key, prompt) -> text


@dataclass
class ProfileSummary:
    created: list[str] = field(default_factory=list)
    fresh: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def refresh_profile(
    repo: Repository,
    settings: Settings,
    symbol: str,
    sec: SecClient,
    generate: Generate = gemini.generate,
) -> str:
    """One company. Returns created | fresh | unsupported | failed. Raises BillingError."""
    company = repo.get_company(symbol)
    if company is None:
        return "failed"
    try:
        filing = sec.latest_annual_filing(symbol)
        stored = repo.latest_profile(symbol)
        if (
            stored is not None
            and stored["accession"] == filing.accession
            and stored["prompt_version"] == gemini.PROMPT_VERSION
        ):
            return "fresh"
        chapters = sec.extract_from(filing)
    except Unsupported:
        return "unsupported"
    except ExtractionFailed as exc:
        repo.add_alert("extraction_failed", f"Profile extraction failed for {symbol}", str(exc))
        return "failed"
    except SecError:
        return "failed"

    prompt = gemini.build_prompt(
        company["name"] or symbol,
        filing.form,
        filing.filing_date,
        company["sector"],
        company["industry"],
        chapters,
    )
    try:
        text = generate(settings.require("google_api_key"), prompt)
    except gemini.BillingError as exc:
        repo.add_alert("billing", "Gemini billing problem", str(exc))
        raise
    except gemini.GeminiError:
        return "failed"
    with repo.transaction():
        repo.upsert_company(
            symbol, sic_description=filing.sic_description, cik=str(filing.cik).zfill(10)
        )
        repo.save_profile(
            symbol,
            text,
            filing.accession,
            gemini.MODEL,
            gemini.PROMPT_VERSION,
            filing.filing_date,
            filing.url,
        )
    return "created"


def refresh_profiles(
    repo: Repository,
    settings: Settings,
    symbols: list[str],
    sec: SecClient | None = None,
    generate: Generate = gemini.generate,
    log: Callable[[str], None] = print,
) -> ProfileSummary:
    sec = sec or SecClient(settings.require("my_email"))
    summary = ProfileSummary()
    for symbol in symbols:
        try:
            outcome = refresh_profile(repo, settings, symbol, sec, generate)
        except gemini.BillingError:
            log("stopping: Gemini billing problem")
            break
        getattr(summary, outcome).append(symbol)
        log(f"{symbol}: {outcome}")
    return summary


def candidate_symbols(repo: Repository) -> list[str]:
    """Candidates of the latest analysed run (quality and opportunity above their thresholds)."""
    from value_scanner.analysis.scoring import is_candidate

    run = repo.latest_analysed_run()
    if run is None:
        return []
    out = []
    for row in repo.stock_table(run["id"]):
        q = (row["scores"].get("quality") or {}).get("score")
        o = (row["scores"].get("opportunity") or {}).get("score")
        if is_candidate(q, o):
            out.append(row["symbol"])
    return out
