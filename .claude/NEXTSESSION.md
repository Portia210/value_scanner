# NEXTSESSION — hand-off log

החדש למעלה. hand-off, לא ארכיון: עד ~120 שורות; למחוק רשומות שהפסיקו להיות רלוונטיות.
כללים קבועים — ב-CLAUDE.md או GOTCHAS.md.

תבנית (להשאיר את שורת "NOT verified"; לכתוב "nothing" אם אין):

    ## YYYY-MM-DD — <task id>: <title>
    - Changed: <what>
    - Verified: <gate, tests, click-through>
    - NOT verified: <what and why>
    - Traps / decisions: <what the next session must know>
    - Next: <what's owed, open questions>

## 2026-11-05 — Gemini billing ובדיקת SEC
- Changed: תיעוד בלבד (R3 ב-ROADMAP, מלכודות ב-GOTCHAS).
- Verified: SEC `companyfacts` ל-AAON תואם ל-StockAnalysis בהכנסות, רווח נקי, נכסים/התחייבויות שוטפים, נכסים, הון עצמי, חוב, תזרים תפעולי ו-capex (עד עיגול), מ-2020 עד 2025; מו"פ קיים ב-SEC בלבד. EPS FY2020 לא מותאם לפיצול; רווח תפעולי שונה בעד ~6%.
- NOT verified: Gemini — עדיין 402 בבדיקה האחרונה. המפתח שייך לפרויקט `value scanner` (`gen-lang-client-0429022801`) שמקושר ל-"My Billing Account" (₪0). **המפתח מחליף ל-"My Billing Account 1" בעצמו** (Cloud Console ← Billing ← Your projects ← ⋮ ← Change billing). Claude לא שינה דבר ולא לחץ "Set account". אחרי זה: `uv run python probes/gemini/business_summary.py --ping --model gemini-3.8-flash`, ואז הרצת הסיכום על AAON (`https://www.sec.gov/Archives/edgar/data/824142/000082414226000005/aaon-20251231.htm`).
- Traps / decisions: ממשק ספק נתונים (StockAnalysis עכשיו, SEC אפשרי בהמשך). הדיון על הפרומפט של הסיכום מחכה לתוצאה הראשונה.
- Next: כתובת קשר ל-SEC (D17), ואז B1.

## 2026-11-05 — מקור נתונים (D7) אומת
- Changed: `probes/screener/probe.py` (הרשאת Bash ייעודית ב-`.claude/settings.local.json`); probe ה-Railway בודק את ה-JSON של הסורק.
- Verified: מקומי — 8 המסננים בקוד = 109 התאמות = הסינון השמור באתר באותו רגע, 20/20 סימבולים בעמוד הראשון. מחיר הסורק = מחיר עמוד המניה (`priceDate` היום). Railway — JSON 200 ×2 (5,600 מניות), 25/25 עמודי דוחות, 0 חסימות.
- NOT verified: ריצה מלאה ארוכה מ-Railway (רק ~27 בקשות).
- Traps / decisions: D7, D16 (מייל, `ALERT_EMAIL_TO`), D18 הוחלטו. עמוד ratios אנונימי מיושן — לא להשתמש. שדות שימושיים בסורק: `nextEarningsDate`, `lastEarningsDate`, `peRatio5Y`, `pOcfRatio`, `grahamUpside`.
- Next: D17 (תיאורי חברה: 10-K + AI? כתובת קשר ל-SEC) ואז B1.

## 2026-11-05 — A1–A3, probe ל-Railway, דוגמת דשבורד
- Changed: ענף `v2` (pushed). A1 (pytest, ruff, hook סריקת סודות שמדלג על lockfiles), A2 (`var/legacy/`), A3 (ניקוי). `probes/railway/` + שירות `probe` בפרויקט Railway `value-scanner` (watch רק על `probes/railway/**`). `frontend/` — דוגמת React + Mantine עם נתוני דמה (בהיר+כהה).
- Verified: gate ירוק; `pnpm -C frontend build`; צילומי מסך של 3 העמודים. probe: מקומי — 30/30 עמודים + סורק בדפדפן עובד; Railway (Singapore) — httpx 30/30 בלי חסימה, **Chromium headless נחסם** (Cloudflare 403) בסורק ובהתחברות.
- NOT verified: התחברות headless מקומית (המשתנים לא נטענים ב-probe מקומי); `screener/initial` ו-`screener/data-points` ב-httpx — **הקריאה נחסמה ע"י מנגנון ההרשאות של Claude Code**, מחכה להחלטת המפתח.
- Traps / decisions: אנונימי מספיק לדוחות (שוליים/FCF עברו ל-`/financials/metrics/`, הכנסות ל-`/financials/income-statement/`, P14). הסינון השמור נשמר ב-Supabase של החשבון (`userdata.screener_views`). המפתח רוצה גם מצב כהה. המפתח הציע סריקה מחדש יום אחרי דוחות — ר' תשובה בשיחה.
- Next: החלטת המפתח על מקור רשימת המניות (JSON של הסורק / דפדפן מקומי / אחר), ואז B1.

## 2026-11-05 — ביקורת ותוכנית v2
- Changed: הועתקו קבצי ה-docs מהתבנית; נכתבו `plans/v2-audit.md`, `plans/v2-rebuild.md`, ROADMAP, ARCHITECTURE (מצב קיים), GOTCHAS; `CLAUDE.md` נכתב מחדש; ל-`PROJECT_OVERVIEW.md` נוספה אזהרה שהוא לא מדויק. **אין שינוי בקוד.**
- Verified: קריאת כל קובצי ה-Python; סקריפטים על 140 המניות ב-`data/` אישרו את R1, R2, R3, R5, P11; `tests/verify_innovation_logic.py` עובר (5 טסטים); אין `.env`/`cookies.txt` בהיסטוריית git; הריפו ציבורי.
- NOT verified: מה הסינון השמור בחשבון StockAnalysis (P5); האם login headless עובד; זמן ריצה מלאה; התנהגות מ-IP של Railway.
- Traps / decisions: המפתח בחר ארכיטקטורה A (שירות אחד, FastAPI + APScheduler + SQLite על Volume). המפתח נתן הרשאה מלאה לשנות מבנה ולערוך כל קובץ. השינויים הלא מקומטים ב-`ken_fisher_check.py` ו-`tests/` שייכים למפתח — לא לגעת לפני D0.
- Next: המפתח עובר על התוכנית ועל החלטות D0–D15 ב-ROADMAP; אחרי אישור מתחילים ב-A1.
