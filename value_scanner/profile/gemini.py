"""Hebrew business profile of a company from the chapters of its annual report (E7, D17).

The chapters are cut out by `sources/sec.py` and sent as text (the model's own URL reader skipped
the MD&A). The API key travels only in a request header. HTTP 402 means billing is not set up
(an alert), 503 is retried a few times, anything else is an error.

PROMPT_VERSION v0 is the probe's prompt (probes/gemini/business_summary.py) adapted to text
input plus sector/industry; the wording is still to be agreed with the developer (D17).
"""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

API = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash"
PROMPT_VERSION = "v0"
RETRIES = 3
RETRY_WAIT = 20.0

PROMPT = """אתה אנליסט השקעות ערך. להלן פרקים מדוח {form} של {company} (דוח שהוגש ב-{filing_date}).
לפי סיווג האתר, הסקטור הוא {sector} והתעשייה {industry}.

כתוב בעברית פרופיל עסקי מעמיק של החברה, למשקיע שלא מכיר אותה. הכללים:
- הסתמך רק על הטקסט שלהלן. אל תוסיף ידע חיצוני ואל תנחש.
- מספרים (הכנסות, אחוזים, מספר עובדים וכו') רק אם הם מופיעים בטקסט, עם שנת הכספים.
- מונחים מקצועיים ושמות מוצרים שאין להם תרגום טוב בעברית — השאר באנגלית
  (למשל HVAC, backlog, OEM, recurring revenue). שמות מגזרים ומותגים — באנגלית.
- היה ספציפי: שמות מוצרים, סוגי לקוחות, שווקים. בלי משפטים כלליים כמו "חברה מובילה".

מבנה התשובה (Markdown, בדיוק הכותרות האלה):
## במשפט אחד
## מה החברה מוכרת
(לכל מגזר: מה הוא מוכר, דוגמאות למוצרים/שירותים, ואחוז מההכנסות אם מופיע)
## מי הלקוחות ואיך החברה מגיעה אליהם
(סוגי לקוחות, ערוצי הפצה, פיזור גיאוגרפי, תלות בלקוח גדול אם יש)
## איך החברה מרוויחה כסף
(מודל עסקי: מכירה חד-פעמית/חוזרת, שירות, חוזים; מה מניע את הרווחיות)
## תחרות ויתרון תחרותי
(מתחרים שהחברה מזכירה, ובמה היא טוענת שהיא שונה)
## מיקום בענף
(לפי תיאור השוק והתחרות בדוח: איפה החברה ממוקמת בתוך התעשייה {industry})
## רגישויות ותלויות
(מחזוריות, עונתיות, חומרי גלם, רגולציה, ריכוזיות ספקים/לקוחות)
## מה קרה בשנה האחרונה
(לפי ה-MD&A: מה הניע את ההכנסות והרווחיות, רכישות, שינויים מהותיים)

הפרקים:
{chapters}
"""


class BillingError(RuntimeError):
    """HTTP 402: the API key's project has no billing (alert-worthy)."""


class GeminiError(RuntimeError):
    pass


def build_prompt(
    company: str,
    form: str,
    filing_date: str,
    sector: str | None,
    industry: str | None,
    chapters: list[tuple[str, str]],
) -> str:
    body = "\n\n".join(f"=== {label} ===\n{text}" for label, text in chapters)
    return PROMPT.format(
        company=company,
        form=form,
        filing_date=filing_date,
        sector=sector or "לא ידוע",
        industry=industry or "לא ידועה",
        chapters=body,
    )


def generate(
    api_key: str,
    prompt: str,
    *,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    model: str = MODEL,
) -> str:
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingLevel": "medium"}},
    }
    own = client is None
    client = client or httpx.Client(timeout=300)
    try:
        for attempt in range(RETRIES):
            try:
                resp = client.post(
                    f"{API}/models/{model}:generateContent",
                    json=body,
                    headers={"x-goog-api-key": api_key},
                )
            except httpx.HTTPError as exc:
                raise GeminiError(f"network error: {type(exc).__name__}") from exc
            if resp.status_code == 402:
                raise BillingError("Gemini answered HTTP 402 (billing)")
            if resp.status_code == 503 and attempt < RETRIES - 1:
                sleep(RETRY_WAIT * (attempt + 1))
                continue
            if resp.status_code != 200:
                raise GeminiError(f"Gemini answered HTTP {resp.status_code}")
            return _text(resp.json())
        raise GeminiError("Gemini unavailable (503)")
    finally:
        if own:
            client.close()


def _text(data: dict) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as exc:
        raise GeminiError("Gemini returned no candidate") from exc
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise GeminiError("Gemini returned an empty answer")
    return text
