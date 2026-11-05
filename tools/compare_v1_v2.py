"""C9: compare the v1 per-criterion results (var/legacy/data/*/report.md) with the v2 results in
the database, criterion by criterion, and say which audit finding could explain each difference.

Usage: uv run python tools/compare_v1_v2.py [--db var/value_scanner.db] [--out var/c9-comparison.md]

Read-only. The full report names symbols and values scraped from StockAnalysis, so it is written
under var/ (git-ignored); only the aggregate counts go into docs/c9-summary.md (`--summary`).

What this can and cannot show: v1 ran on FY2024 data and FY-end prices, v2 on FY2025/TTM data and
today's prices, so a status can differ because the *data* moved, not only because the logic
changed. A difference is therefore reported with the audit findings that *could* explain it plus
the v1 text and the v2 value side by side; it is not proven by this script.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import Counter
from pathlib import Path

LEGACY = Path("var/legacy/data")

# v1 line label (section, label) -> (v2 guru, v2 criterion, audit findings that may explain a flip)
MAP: dict[tuple[str, str], tuple[str, str, tuple[str, ...]]] = {
    ("Basic", "current ratio"): ("screen", "current_ratio", ("R1",)),
    ("Basic", "profit margin"): ("screen", "profit_margin", ("R1", "R10")),
    ("Basic", "ROE"): ("screen", "roe_5y", ("R10",)),
    ("Basic", "working capital vs long-term debt"): ("graham", "working_capital", ()),
    ("Graham", "market cap"): ("screen", "market_cap", ("R1",)),
    ("Graham", "revenue"): ("graham", "sales", ()),
    ("Graham", "working capital vs debt"): ("graham", "working_capital", ()),
    ("Graham", "P/E ratio"): ("graham", "pe", ("R1", "R5")),
    ("Graham", "graham number"): ("graham", "graham_number", ("R1", "R5")),
    ("Graham", "EPS growth"): ("graham", "eps_growth", ("R2",)),
    ("Fisher", "Valuation"): ("fisher", "ps", ("R1", "R4", "R5", "R8", "R9")),
    ("Fisher", "Net Profit Margin"): ("fisher", "net_margin", ("R6",)),
    ("Fisher", "EPS Growth"): ("fisher", "eps_growth", ("R3",)),
    ("Fisher", "Debt-to-Equity"): ("fisher", "debt_equity", ("F5-DE",)),
    ("Fisher", "FCF/Share"): ("fisher", "fcf", ()),
    ("Fisher", "Innovation Factor"): ("fisher", "rd", ("R7",)),
}
# Ids that are not audit findings: F5-DE = v2 follows the lesson-5 formula page (total liabilities /
# equity), v1 used the site's Total Debt / Equity ratio at FY end.
# v1 checks with no v2 counterpart (the lessons do not ask for them: audit R10)
V1_ONLY = {("Basic", "net income"), ("Basic", "operating margin")}
V1_STATUS = {"PASS": "PASS", "FAIL": "FAIL", "N/A": "NA"}
_LINE = re.compile(r"^- (?P<label>.+?)\s*(?:\([^)]*\))?\s*:\s*(?P<rest>.*)$")
_SECTION = (("Basic Reports Check", "Basic"), ("Benjamin Graham Check", "Graham"),
            ("Ken Fisher Super Stocks Check", "Fisher"))


def parse_v1_report(text: str) -> dict[tuple[str, str], tuple[str, str]]:
    """(section, label) -> (status, v1 explanation text)."""
    out: dict[tuple[str, str], tuple[str, str]] = {}
    section = None
    for line in text.splitlines():
        if line.startswith(">"):
            section = next((s for key, s in _SECTION if key in line), section)
            continue
        if section is None or not line.startswith("- ") or "Classification" in line:
            continue
        m = _LINE.match(line.replace("**", ""))
        if not m:
            continue
        rest = m.group("rest")
        status = next(
            (v for k, v in V1_STATUS.items() if re.search(rf"\b{re.escape(k)}\b", rest)), None
        )
        if status is None:
            continue
        label = re.sub(r"\s+", " ", m.group("label")).strip()
        label = re.sub(r"\s*\(.*$", "", label).strip()
        out[(section, label)] = (status, rest.strip())
    return out


def v2_results(db: sqlite3.Connection) -> dict[tuple[str, str, str], tuple[str, float | None]]:
    run = db.execute(
        "SELECT MAX(run_id) FROM scores WHERE kind = 'quality'"
    ).fetchone()[0]
    return {
        (s, g, c): (st, v)
        for s, g, c, st, v in db.execute(
            "SELECT symbol, guru, criterion_id, status, value FROM results WHERE run_id = ?",
            (run,),
        )
    }


def compare(db_path: str) -> tuple[list[dict], Counter, set[str], set[str]]:
    db = sqlite3.connect(db_path)
    v2 = v2_results(db)
    v2_symbols = {k[0] for k in v2}
    v1_reports = {p.parent.name: parse_v1_report(p.read_text(encoding="utf-8"))
                  for p in sorted(LEGACY.glob("*/report.md"))}
    rows, counts = [], Counter()
    for symbol, checks in v1_reports.items():
        if symbol not in v2_symbols:
            continue
        for key, (status1, text1) in checks.items():
            if key in V1_ONLY:
                counts["only in v1 (not in the lessons)"] += 1
                continue
            if key not in MAP:
                counts["unmapped v1 check"] += 1
                rows.append({"symbol": symbol, "check": key, "kind": "UNMAPPED", "v1": status1,
                             "v2": "-", "why": (), "v1_text": text1, "v2_value": None})
                continue
            guru, cid, why = MAP[key]
            status2, value2 = v2.get((symbol, guru, cid), ("MISSING", None))
            if status1 == status2:
                counts["same"] += 1
                continue
            kind = "NA in v2" if status2 == "NA" else "DIFFERENT"
            counts[kind] += 1
            rows.append({"symbol": symbol, "check": key, "kind": kind, "v1": status1, "v2": status2,
                         "why": why, "v1_text": text1, "v2_value": value2,
                         "v2_id": f"{guru}.{cid}"})
    return rows, counts, set(v1_reports), v2_symbols


def render(rows, counts, v1_symbols, v2_symbols) -> str:
    both = v1_symbols & v2_symbols
    lines = [
        "# C9 - v1 vs v2, per criterion",
        "",
        f"v1 stocks: {len(v1_symbols)} · v2 stocks (latest run): {len(v2_symbols)} · "
        f"in both: {len(both)}",
        f"Not compared (in only one of them): v1-only {len(v1_symbols - v2_symbols)}, "
        f"v2-only {len(v2_symbols - v1_symbols)} - the saved screen of the account (v1) and the "
        "screen rebuilt in code (v2, decision D7) are different universes (audit P5).",
        "",
        "Criterion comparisons: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())),
        "",
        "Every status flip is listed with the audit findings that could explain it. "
        "**Data moved too** (v1: FY2024 and FY-end prices; v2: FY2025/TTM and today's prices), so "
        "a flip is not proof of a logic change - compare the v1 text with the v2 value.",
        "",
        "| symbol | v1 check | v2 criterion | v1 | v2 | v2 value | may be explained by | v1 said |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: (r["check"], r["symbol"])):
        value = "" if r["v2_value"] is None else f"{r['v2_value']:.4g}"
        why = ", ".join(r["why"]) or "data only (no logic change known)"
        lines.append(
            f"| {r['symbol']} | {r['check'][1]} | {r.get('v2_id', '-')} | {r['v1']} | {r['v2']} | "
            f"{value} | {why} | {r['v1_text'][:90].replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def summary(rows, counts) -> str:
    by_check = Counter((r["check"][1], r["kind"]) for r in rows)
    no_logic = Counter(r["check"][1] for r in rows if not r["why"] and r["kind"] == "DIFFERENT")
    lines = [
        "# סיכום C9 - השוואת v1 ל-v2 (מספרים בלבד)",
        "",
        "נוצר ע\"י `tools/compare_v1_v2.py`; הדוח המלא (עם סימולים וערכים) "
        "ב-`var/c9-comparison.md`, מחוץ ל-git.",
        "",
        "השוואה לפי קריטריון על המניות שקיימות גם ב-v1 וגם ב-v2. **שימו לב:** v1 רץ על "
        "דוחות FY2024 ומחירי סוף שנה, v2 על FY2025/TTM ומחיר נוכחי, ולכן שינוי סטטוס אינו בהכרח הוכחה לשינוי "
        "לוגיקה.",
        "",
        "מפתח: R1-R10 = ממצאי הביקורת (`.claude/plans/v2-audit.md`); "
        "F5-DE = v2 לפי דף הנוסחאות של שיעור 5 "
        "(סך התחייבויות / הון), v1 לפי Total Debt / Equity של האתר.",
        "",
        "| תוצאה | כמות |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(counts.items())],
        "",
        "## שינויים לפי קריטריון ב-v1",
        "",
        "| בדיקה ב-v1 | סוג | כמות |",
        "|---|---|---|",
        *[f"| {c} | {k} | {n} |" for (c, k), n in sorted(by_check.items())],
        "",
        "## שינויים שאין להם ממצא ביקורת מוכר (רק שינוי נתונים אפשרי)",
        "",
        *[f"- {c}: {n}" for c, n in sorted(no_logic.items())],
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="var/value_scanner.db")
    ap.add_argument("--out", default="var/c9-comparison.md")
    ap.add_argument("--summary", default="docs/c9-summary.md")
    args = ap.parse_args()
    rows, counts, v1s, v2s = compare(args.db)
    Path(args.out).write_text(render(rows, counts, v1s, v2s), encoding="utf-8")
    Path(args.summary).write_text(summary(rows, counts), encoding="utf-8")
    print(f"{len(rows)} differences; counts: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
