"""docs/criteria/*.md generated from the criteria definitions in code (C10).

The files are never edited by hand: `python -m value_scanner docs` rewrites them and a test fails
if they drift from the code.
"""

from __future__ import annotations

from pathlib import Path

from value_scanner.analysis.criteria import Criterion
from value_scanner.analysis.gurus import fisher, graham, piotroski, screen

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "criteria"

GURUS = {
    "screen": ("שיעור 3 - סינון ראשוני", screen.CRITERIA),
    "graham": ("שיעור 4 - בנג'מין גראהם", graham.CRITERIA),
    "fisher": ("שיעור 5 - קן פישר", fisher.CRITERIA),
    "piotroski": ("שיעור 6 - יוסף פיוטרוסקי", piotroski.CRITERIA),
}

HEADER = (
    "<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: "
    "python -m value_scanner docs. לא לערוך ידנית. -->\n"
)
SCORING = """
## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
"""


def _threshold(c: Criterion) -> str:
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
    return {f"{guru}.md": render(guru) for guru in GURUS}


def write_all(directory: Path = DOCS_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in render_all().items():
        path = directory / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
