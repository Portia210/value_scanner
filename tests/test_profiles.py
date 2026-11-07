import json

import httpx
import pytest

from tests.test_analyze import run_with, seed
from value_scanner.jobs.analyze import analyse_run
from value_scanner.jobs.profiles import candidate_symbols, refresh_profile, refresh_profiles
from value_scanner.profile import gemini
from value_scanner.settings import load_settings
from value_scanner.sources import sec
from value_scanner.sources.sec import (
    ExtractionFailed,
    SecClient,
    Unsupported,
    extract_chapter,
    extract_chapters,
    html_to_text,
)
from value_scanner.storage import db
from value_scanner.storage.repo import Repository

FILLER = "The company designs and sells widgets to industrial customers worldwide. " * 120


def tenk_html(business=FILLER, risk="Risk text. " * 400, mdna=FILLER, toc=True):
    contents = (
        "<p>Item 1. Business</p><p>3</p><p>Item 1A. Risk Factors</p><p>9</p>"
        "<p>Item 7. Management's Discussion</p><p>30</p>"
        if toc
        else ""
    )
    return (
        f"<html><body><p>Table of contents</p>{contents}"
        f"<p>ITEM 1. BUSINESS</p><p>{business}</p>"
        f"<p>ITEM 1A. RISK FACTORS</p><p>{risk}</p>"
        "<p>ITEM 1B. UNRESOLVED STAFF COMMENTS</p><p>None.</p>"
        f"<p>ITEM 7. MANAGEMENT'S DISCUSSION</p><p>{mdna}</p>"
        "<p>ITEM 7A. MARKET RISK</p><p>Small.</p>"
        "<p>ITEM 8. FINANCIAL STATEMENTS</p><p>numbers</p></body></html>"
    )


def test_chapters_skip_the_table_of_contents_and_stop_at_the_next_item():
    text = html_to_text(tenk_html())
    business = extract_chapter(text, "1")
    assert business.startswith("ITEM 1. BUSINESS") and "RISK FACTORS" not in business
    assert len(business) > 5000
    assert extract_chapter(text, "7").strip().endswith(FILLER.strip())  # stops before 7A
    labels = [label for label, _ in extract_chapters(text, "10-K")]
    assert labels == ["Item 1. Business", "Item 1A. Risk Factors", "Item 7. MD&A"]


def test_short_required_chapter_is_an_extraction_failure_but_missing_risk_factors_is_fine():
    with pytest.raises(ExtractionFailed, match="Item 1"):
        extract_chapters(html_to_text(tenk_html(business="tiny")), "10-K")
    no_risk = html_to_text(tenk_html(risk=""))
    assert [lbl for lbl, _ in extract_chapters(no_risk, "10-K")][0] == "Item 1. Business"
    with pytest.raises(Unsupported):
        extract_chapters("x", "40-F")


def test_20f_chapters():
    html = (
        "<p>Item 3. Key Information</p><p>A. Reserved</p><p>D. Risk Factors</p>"
        f"<p>{'We face risk. ' * 50}</p><p>Item 4. Information on the Company</p>"
        f"<p>{FILLER}</p><p>Item 5. Operating and Financial Review</p><p>{FILLER}</p>"
        "<p>Item 6. Directors</p><p>x</p>"
    )
    labels = [lbl for lbl, _ in extract_chapters(html_to_text(html), "20-F")]
    assert labels == [
        "Item 4. Information on the Company",
        "Item 3.D Risk Factors",
        "Item 5. Operating and Financial Review",
    ]


SUBMISSIONS = {
    "sicDescription": "Air Conditioning",
    "filings": {
        "recent": {
            "form": ["8-K", "10-K", "10-K"],
            "accessionNumber": [
                "0000000001-26-000001",
                "0000000002-26-000002",
                "0000000002-25-000003",
            ],
            "filingDate": ["2026-05-01", "2026-02-20", "2025-02-20"],
            "primaryDocument": ["x.htm", "aaa-20251231.htm", "aaa-20241231.htm"],
        }
    },
}


def sec_handler(html=None, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        url = str(request.url)
        if url == sec.TICKERS_URL:
            return httpx.Response(200, json={"0": {"ticker": "AAA", "cik_str": 123, "title": "A"}})
        if url == sec.SUBMISSIONS_URL.format(cik=123):
            return httpx.Response(200, json=SUBMISSIONS)
        if url.endswith("aaa-20251231.htm"):
            return httpx.Response(200, text=html or tenk_html())
        return httpx.Response(404)

    return handler


def sec_client(html=None, seen=None):
    transport = httpx.MockTransport(sec_handler(html, seen))
    return SecClient("me@example.com", httpx.Client(transport=transport), sleep=lambda s: None)


def test_latest_annual_filing_skips_other_forms_and_builds_the_archive_url():
    filing = sec_client().latest_annual_filing("AAA")
    assert (filing.form, filing.accession, filing.filing_date) == (
        "10-K",
        "0000000002-26-000002",
        "2026-02-20",
    )
    assert (
        filing.url
        == "https://www.sec.gov/Archives/edgar/data/123/000000000226000002/aaa-20251231.htm"
    )
    with pytest.raises(Unsupported):
        sec_client().latest_annual_filing("ZZZ")


def test_user_agent_carries_the_contact_address():
    client = SecClient("me@example.com", sleep=lambda s: None)
    assert "me@example.com" in client._client.headers["User-Agent"]


@pytest.fixture
def repo():
    return Repository(db.open_database(":memory:"))


SETTINGS = load_settings(
    {"DB_PATH": ":memory:", "GOOGLE_API_KEY": "k" * 10, "MY_EMAIL": "me@example.com"}
)


def test_profile_is_created_once_and_refreshed_only_for_a_new_report(repo):
    repo.upsert_company("AAA", name="Alpha Corp", sector="Industrials", industry="Machinery")
    prompts = []

    def fake_generate(key, prompt):
        prompts.append(prompt)
        return "## במשפט אחד\nחברה."

    assert refresh_profile(repo, SETTINGS, "AAA", sec_client(), fake_generate) == "created"
    stored = repo.latest_profile("AAA")
    assert stored["accession"] == "0000000002-26-000002" and stored["filing_date"] == "2026-02-20"
    assert stored["source_url"].endswith("aaa-20251231.htm") and "חברה" in stored["text"]
    assert (
        "Alpha Corp" in prompts[0] and "Industrials" in prompts[0] and "Item 7. MD&A" in prompts[0]
    )
    company = repo.get_company("AAA")
    assert company["cik"] == "0000000123" and company["sic_description"] == "Air Conditioning"

    # same accession and prompt version -> nothing to do, no second Gemini call
    assert refresh_profile(repo, SETTINGS, "AAA", sec_client(), fake_generate) == "fresh"
    assert len(prompts) == 1


def test_extraction_failure_raises_an_alert_and_does_not_call_gemini(repo):
    repo.upsert_company("AAA", name="Alpha")
    called = []
    outcome = refresh_profile(
        repo, SETTINGS, "AAA", sec_client(tenk_html(business="tiny")), lambda k, p: called.append(1)
    )
    assert outcome == "failed" and not called
    alert = repo.conn.execute("SELECT kind, subject FROM alerts").fetchone()
    assert alert["kind"] == "extraction_failed" and "AAA" in alert["subject"]


def test_billing_error_alerts_and_stops_the_batch(repo):
    for s in ("AAA", "BBB"):
        repo.upsert_company(s, name=s)

    def billing(key, prompt):
        raise gemini.BillingError("402")

    summary = refresh_profiles(
        repo, SETTINGS, ["AAA", "BBB"], sec_client(), billing, log=lambda m: None
    )
    assert summary.created == [] and summary.failed == []  # stopped at the first
    assert repo.conn.execute("SELECT kind FROM alerts").fetchone()["kind"] == "billing"


def gemini_client(responses):
    calls = iter(responses)
    return httpx.Client(transport=httpx.MockTransport(lambda request: next(calls)))


OK = {"candidates": [{"content": {"parts": [{"text": " שלום "}]}}]}


def test_gemini_retries_503_and_reports_402_and_other_errors():
    waits = []
    client = gemini_client([httpx.Response(503), httpx.Response(200, json=OK)])
    assert gemini.generate("k", "p", client=client, sleep=waits.append) == "שלום"
    assert waits == [20.0]
    with pytest.raises(gemini.BillingError):
        gemini.generate("k", "p", client=gemini_client([httpx.Response(402)]))
    with pytest.raises(gemini.GeminiError, match="503"):
        gemini.generate(
            "k", "p", client=gemini_client([httpx.Response(503)] * 3), sleep=lambda s: None
        )
    with pytest.raises(gemini.GeminiError, match="empty"):
        gemini.generate(
            "k",
            "p",
            client=gemini_client(
                [httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": ""}]}}]})]
            ),
        )


def test_api_key_goes_in_a_header_never_in_the_url():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=OK)

    gemini.generate("secret-key", "p", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert (
        "secret-key" not in str(seen[0].url) and seen[0].headers["x-goog-api-key"] == "secret-key"
    )
    assert json.loads(seen[0].content)["contents"][0]["parts"][0]["text"] == "p"


def test_candidate_symbols_come_from_the_latest_analysed_run(repo):
    run = run_with(repo, [seed(repo, "AAA"), seed(repo, "BBB", pe_ratio=90.0, pb_ratio=9.0)])
    analyse_run(repo, run)
    repo.finish_run(run, "ok")
    assert "BBB" not in candidate_symbols(repo)
    assert isinstance(candidate_symbols(repo), list)


def sse(*pieces: str, tail: str = "") -> bytes:
    events = [json.dumps({"candidates": [{"content": {"parts": [{"text": t}]}}]}) for t in pieces]
    return ("".join(f"data: {e}\r\n\r\n" for e in events) + tail).encode()


def test_stream_delivers_every_piece_and_returns_the_whole_answer():
    got = []
    client = gemini_client([httpx.Response(200, content=sse("## א\n", "שלום ", "עולם "))])
    assert gemini.generate_stream("k", "p", got.append, client=client) == "## א\nשלום עולם"
    assert got == ["## א\n", "שלום ", "עולם "]


def test_stream_retries_503_reports_402_and_mid_stream_errors_and_empty_answers():
    waits = []
    ok = httpx.Response(200, content=sse("שלום"))
    client = gemini_client([httpx.Response(503), ok])
    assert (
        gemini.generate_stream("k", "p", lambda t: None, client=client, sleep=waits.append)
        == "שלום"
    )
    assert waits == [20.0]
    with pytest.raises(gemini.BillingError):
        gemini.generate_stream(
            "k", "p", lambda t: None, client=gemini_client([httpx.Response(402)])
        )
    failing = httpx.Response(200, content=sse("חלק", tail='data: {"error": {"code": 500}}\r\n\r\n'))
    with pytest.raises(gemini.GeminiError, match="error"):
        gemini.generate_stream("k", "p", lambda t: None, client=gemini_client([failing]))
    with pytest.raises(gemini.GeminiError, match="empty"):
        gemini.generate_stream(
            "k", "p", lambda t: None, client=gemini_client([httpx.Response(200, content=b"")])
        )
    with pytest.raises(gemini.GeminiError, match="503"):
        gemini.generate_stream(
            "k",
            "p",
            lambda t: None,
            sleep=lambda s: None,
            client=gemini_client([httpx.Response(503)] * 3),
        )


def test_stream_key_is_a_header_and_url_asks_for_sse():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=sse("x"))

    gemini.generate_stream(
        "secret-key",
        "p",
        lambda t: None,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert "secret-key" not in str(seen[0].url) and "alt=sse" in str(seen[0].url)
    assert seen[0].headers["x-goog-api-key"] == "secret-key"


def test_on_demand_job_shows_the_text_so_far_and_keeps_nothing_until_the_end(tmp_path):
    import threading

    from value_scanner.jobs import profiles as pj
    from value_scanner.settings import load_settings

    env = {"DB_PATH": str(tmp_path / "p.db"), "GOOGLE_API_KEY": "k" * 10, "MY_EMAIL": "me@e.com"}
    settings = load_settings(env)
    db.open_database(env["DB_PATH"]).close()
    first_piece, release = threading.Event(), threading.Event()

    def fake_stream(api_key, prompt, on_text, **kw):
        on_text("## במשפט")
        on_text(" אחד")
        first_piece.set()
        release.wait(5)
        return "## במשפט אחד"

    def fake_refresh(repo, settings, symbol, sec, generate=None):
        generate("k", "p")
        return "created"

    originals = gemini.generate_stream, pj.refresh_profile, pj.SecClient
    gemini.generate_stream, pj.refresh_profile, pj.SecClient = (
        fake_stream,
        fake_refresh,
        lambda contact: None,
    )
    try:
        assert pj.start_profile(settings, "ZZZ") is True
        assert first_piece.wait(5)
        assert pj.profile_job_status("ZZZ") == "running"
        assert pj.profile_job_text("ZZZ") == "## במשפט אחד"
        release.set()
        for _ in range(200):
            if pj.profile_job_status("ZZZ") != "running":
                break
            threading.Event().wait(0.02)
        assert pj.profile_job_status("ZZZ") == "ok"
        assert pj.profile_job_text("ZZZ") == ""  # the finished text lives in the database
    finally:
        gemini.generate_stream, pj.refresh_profile, pj.SecClient = originals
