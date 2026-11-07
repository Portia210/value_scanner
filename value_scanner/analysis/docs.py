"""docs/criteria/*.md generated from the criteria definitions in code (C10).

The files are never edited by hand: `python -m value_scanner docs` rewrites them and a test fails
if they drift from the code.
"""

from __future__ import annotations

from pathlib import Path

from value_scanner.analysis.criteria import Criterion
from value_scanner.analysis.gurus import buffett, fisher, graham, neff, piotroski, screen
from value_scanner.analysis.scoring import (
    CANDIDATE_OPPORTUNITY,
    CANDIDATE_QUALITY,
    FAIR_PE_DEFAULT,
    FAIR_PE_TECH,
    GRAHAM_PRODUCT,
    MIN_COVERAGE,
)

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "criteria"

GURUS = {
    "screen": ("שיעור 3 - סינון ראשוני", screen.CRITERIA),
    "graham": ("שיעור 4 - בנג'מין גראהם", graham.CRITERIA),
    "fisher": ("שיעור 5 - קן פישר", fisher.CRITERIA),
    "piotroski": ("שיעור 6 - יוסף פיוטרוסקי", piotroski.CRITERIA),
    "buffett": ("שיעור 7 - וורן באפט", buffett.CRITERIA),
    "neff": ("שיעור 8 - ג'ון נף", neff.CRITERIA),
}

HEADER = (
    "<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: "
    "python -m value_scanner docs. לא לערוך ידנית. -->\n"
)
SCORING = """
## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- שורה `MANUAL` ("בדיקה אנושית") אי אפשר לחשב מהדוחות: היא בטבלה, ואינה נספרת בציון או בכיסוי.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
"""


# The four buy-opportunity components (scoring.opportunity_components), with the formula text
# shown on the "how it is calculated" page.
OPPORTUNITY_DOCS = {
    "graham_number": (
        "Graham number",
        f"1 - sqrt(P/E x P/B / {GRAHAM_PRODUCT:g})  (not technology; P/E and P/B positive)",
    ),
    "fair_pe": (
        "Fair P/E",
        f"1 - P/E / fair P/E  (fair P/E {FAIR_PE_DEFAULT:g}, technology {FAIR_PE_TECH:g}; "
        "P/E positive)",
    ),
    "vs_history": (
        "Versus its own history",
        "1 - P/E / 5-year P/E  (the screener's 5-year average P/E; both positive)",
    ),
    "price_sales": (
        "Price to sales",
        "1 - P/S / limit  (limit 0.8 cyclical, 1.5 other; not technology; P/S positive)",
    ),
}

OPPORTUNITY_NOTE = (
    "- ציון ההזדמנות הוא **החציון** של הרכיבים שחלים על המניה (אין רכיב שחל = אין ציון).\n"
    f"- מועמדת לקנייה: איכות ≥ {CANDIDATE_QUALITY:g} **וגם** הזדמנות ≥ {CANDIDATE_OPPORTUNITY:g}.\n"
    f"- איכות = ממוצע ציוני הגורואים שדורגו (לפחות שניים); גורו עם כיסוי מתחת ל-{MIN_COVERAGE:.0%} "
    "אינו מדרג."
)



def render_opportunity() -> str:
    lines = [
        HEADER,
        "# הזדמנות קנייה (מרווח ביטחון)\n",
        "לכל מניה ארבעה רכיבים אפשריים, כולם במחיר הנוכחי. רכיב שאינו חל על המניה אינו נספר.\n",
        "| מזהה | רכיב | נוסחה |",
        "|---|---|---|",
    ]
    for cid, (title, formula) in OPPORTUNITY_DOCS.items():
        lines.append(f"| `{cid}` | {title} | {formula} |")
    return "\n".join(lines) + "\n\n## איך זה נכנס לציון\n\n" + OPPORTUNITY_NOTE + "\n"


def _threshold(c: Criterion) -> str:
    if c.manual:
        return "בדיקה אנושית"
    return f"{c.direction} {c.threshold:g}"


def render(guru: str) -> str:
    title, criteria = GURUS[guru]
    lines = [
        HEADER,
        f"# {title}\n",
        "| # | מזהה | מבחן | נוסחה | סף | הערות |",
        "|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(criteria.values(), start=1):
        lines.append(
            f"| {i} | `{c.id}` | {c.title} | {c.formula} | `{_threshold(c)}` | {c.note or '—'} |"
        )
    return "\n".join(lines) + "\n" + SCORING


def render_all() -> dict[str, str]:
    files = {f"{guru}.md": render(guru) for guru in GURUS}
    files["opportunity.md"] = render_opportunity()
    return files


def write_all(directory: Path = DOCS_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in render_all().items():
        path = directory / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
