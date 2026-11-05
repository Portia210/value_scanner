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

## 2026-11-05 — תיקון: דפי הדוחות הם כמה טבלאות (D19 בוטל)
- Changed: `parse_statement_table` קורא את **כל** טבלאות `table.financials-table` בעמוד; סיומות K/M/B/T מומרות למיליונים; שם שחוזר — הראשון מנצח. `metrics` מחוץ לברירת המחדל. B4 (קוד): `jobs/pipeline.py`, `jobs/alerts.py`, `cli.py run [--limit N]`, `SMTP_*`.
- Verified: gate ירוק (137). חי על AAON: income 228 שורות (כולל FCF), balance_sheet 288 (התחייבויות, הון, חוב), cash_flow 246 (capex, FCF). ריצה ראשונה: 5,601 מניות, 108 עוברות; הופסקה ידנית → `interrupted`, נעילה שוחררה.
- NOT verified: ריצה מלאה וזמנה (B4 עדיין פתוח); מייל אמיתי (אין SMTP); שמות שורות מול v1 (ר' GOTCHAS); `Profit Margin` לא נמצא בשם הזה ברווח והפסד.
- Traps / decisions: **טעיתי** בדיווח קודם שהאתר קוטע דוחות — המשתמש הראה צילום מסך של התחייבויות באתר. הבדיקה שלי קראה רק טבלה ראשונה (גם בדפדפן). שנים ישנות (2016–2020) הן `Upgrade` ולכן 5 FY + TTM בלבד.
- Next: ריצה מלאה מקומית למדידת זמן (סוגרת B4), ואז C1.

## 2026-11-05 — B1: הורדת דוחות
- Changed: `sources/stockanalysis.py` (פענוח הטבלה לפורמט ארוך, `StatementFetcher` עם סיווג ok/blocked/failed/no_table וניסיונות חוזרים חסומים), `jobs/refresh.py` (כללי D18: חדש מיד, ניסיונות 1/3/7 ימים אחרי `lastEarningsDate` עד שהטבלה משתנה, ריענון מלא כל 45 יום; לולאת הורדה איטית), `tests/test_statements.py`.
- Verified: gate ירוק (122 טסטים: 200/404/429/אתגר/בלי טבלה/טבלה פגומה/שגיאת רשת, גבולות D18, קצב 3–6 שנ' והפסקה ארוכה, חסימה → המתנה וניסיון חוזר → הפסקת האצווה אחרי 3). **בקשה חיה אחת** ל-AAON income: 138 שורות, FY 2024 תואם ל-v1 (Revenue 1201, EPS 2.02, Net Income 168.56).
- NOT verified: ריצה ארוכה על מאות עמודים; `metrics`/`balance_sheet`/`cash_flow` לא נבדקו חיים (רק income); עמוד חסום אמיתי; מניות עם נקודה בסימבול (`brk.b` בכתובת — מתוך hrefs של v1, לא נבדק חי).
- Traps / decisions: שמות שורות באתר השתנו מ-v1 (GOTCHAS). `ratios` מוגדר ב-`STATEMENT_PATHS` אבל מחוץ ל-`DEFAULT_STATEMENTS` (סתירה בין ROADMAP B1 ל-GOTCHAS — בחרתי ב-GOTCHAS; לשנות אם רוצים). `latest_period` = שנת ה-FY האחרונה (בלי TTM), ולכן ריבוע חדש (TTM) מתגלה רק דרך השוואת ערכים. כשל/no_table לא נספרים כניסיון ב-D18; מניה כושלת תנוסה שוב בכל ריצה.
- Next: B4 (`pipeline.py` + `cli.py run` + מייל) — מחבר `refresh_universe` ← `download_statements`; פרטי SMTP.

## 2026-11-05 — B3: רשימת מניות מה-JSON של הסורק
- Changed: `sources/screener.py` (שתי בקשות איטיות, 8 מסננים בקוד, dedupe סדרות, `Blocked`/`StructureChanged`), `jobs/universe.py` (snapshots ל-DB, כניסות/יציאות עם סיבה, התראה בטבלת `alerts`), `tests/factories.py`.
- Verified: gate ירוק (81 טסטים); על ה-JSON השמור ב-`var/probe-screener`: 5,600 מניות → 109 עוברות (כמו ב-probe) → 107 אחרי dedupe (GOOG, HEI.A נשמטות); 967 "כמעט" (נכשלות עד 2 מסננים).
- NOT verified: **לא הורץ מול האתר החי** (הקוד נבדק עם httpx mock ועם JSON שמור); מזהי data-points `pOcfRatio`, `peRatio5Y`, `priceDate`, `lastEarningsDate`, `nextEarningsDate` קיימים בקטלוג אבל הערכים שלהם לא נבדקו בתשובה אמיתית; שליחת המייל בפועל (B4).
- Traps / decisions: ערך חסר במסנן = לא עובר (ונספר ב-`filters_failed`). השוואת חברות בין ריצות לפי שם, לא סימבול, כדי שהחלפת סדרה (GOOG↔GOOGL) לא תיראה כיציאה. מניה שנכנסה בלי snapshot קודם אבל מוכרת → סיבה `data`. שדה סינון שמלא ב-<15% מהמניות = שינוי מבנה; ירידה מתחת ל-70% בכמות = שינוי מבנה (נבדק מול `universe_count` ב-settings).
- Next: B1 (הורדת דוחות); אחר כך B4.

## 2026-11-05 — A4 + D1: שלד חבילה ומסד נתונים
- Changed: `value_scanner/` — `settings.py` (env בלבד, סודות מוסתרים מ-repr), `cli.py` (`--help`, `config`; `run`/`serve`/`docs` עדיין stubs עם קוד יציאה 2), `.env.example`. `storage/migrations/0001_initial.sql` (15 טבלאות לפי §2), `storage/db.py` (WAL, foreign keys, מיגרציות ממוספרות), `storage/repo.py` (הנקודה היחידה מול ה-DB; מדיניות שמירה).
- Verified: gate ירוק (35 טסטים, מתוכם 24 על DB בזיכרון: נעילת ריצה, שמירת 4 הורדות, NA, CHECK על סטטוס/strength, שמירה לפי חלונות זמן, rollback); `python -m value_scanner --help` ו-`config` עובדים.
- NOT verified: מעבר ל-Postgres (ids הם `INTEGER PRIMARY KEY` — שם יידרש IDENTITY); ביצועים על נפח אמיתי; `config` מול `.env` אמיתי הראה רק set/unset.
- Traps / decisions: נעילת הריצה = אינדקס ייחודי חלקי על `runs(status) WHERE status='running'`. `save_statement_fetch` גוזם רק הורדות `ok`; הורדות שנכשלו נמחקות אחרי 90 יום. `classifications` ו-`score_components` בפורמט שורות (גמיש ל-D6/D9). הסכמה עוד לא נבדקה מול הצרכים של B1/B3 — מיגרציה 0002 אם צריך. מילת-קסם `pragma: allowlist secret` נדרשה בטסט (סיסמת דמה).
- Next: B1 (הורדת דוחות) או B3 (רשימת מניות מה-JSON) — שתיהן כותבות דרך `Repository`.

## 2026-11-05 — הכול במסד נתונים, MY_EMAIL
- Changed: תיעוד בלבד. `plans/v2-rebuild.md` §2: אין תיקיית נתונים; כל המידע ב-SQLite (הגדרות, חברות, snapshots של הסורק, דוחות בפורמט ארוך, תוצאות, ציונים, אירועי מעקב, פרופילים, התראות). `sources/` עם ממשק ספק במקום `scraper/`; בלי login/Playwright/עוגיות. ROADMAP: B2 בוטל, B1/B3/B4/D1/F1/F2 עודכנו; **D1 מבוצע מיד אחרי A4**.
- Verified: עקביות המסמכים (grep); אין שינוי בקוד.
- NOT verified: מבנה הסכמה בפועל (D1); נפח ה-DB (הערכה: עשרות MB בשנה).
- Traps / decisions: D16 — משתנה אחד `MY_EMAIL` לנמען ההתראות ולכתובת הקשר מול ה-SEC; לא נכנס לקוד, ללוגים או ל-git. פרטי שליחת מייל (`SMTP_*`) ייקבעו ב-B4. SQLite נשאר; מעבר ל-Postgres אפשרי דרך שכבת ה-repository.
- Next: A4 (שלד חבילה + settings), ואז D1.

## 2026-11-05 — פרופיל חברה עם Gemini נבדק
- Changed: תיעוד (D17, E7, GOTCHAS). הפלט: `var/probe-gemini/aaon.md` (לא ב-git).
- Verified: החיוב תוקן (ping 200). AAON: 113 שניות, ~57K טוקנים, 8/8 עובדות שנבדקו נכונות (הכנסות חוץ, זמני אספקה, שלושה לקוחות מעל 10% ב-2025, שותפי הפצה, חברות חוות שרתים שהדוח מזכיר כדוגמאות שוק ולא כלקוחות).
- NOT verified: חברות מסוגים אחרים (פארמה, פיננסית, זרה/20-F); עלות בכסף.
- Traps / decisions: `url_context` קורא רק חלק מהדוח ופספס את ה-MD&A — חיתוך הפרקים בקוד שלנו. הפרומפט לא נסגר; מחכה לדיון עם המפתח.
- Next: דיון בפרומפט, כתובת קשר ל-SEC, ואז B1.

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
