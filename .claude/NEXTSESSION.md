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

## 2026-11-08 — שיעורים 7 ו-8: באפט ונף
- Changed: `gurus/buffett.py` (6 מבחנים כמותיים + 4 שורות `MANUAL` "בדיקה אנושית": 3 איכותיות ו-DCF), `gurus/neff.py` (7 מבחנים). `Status.MANUAL` לא נספר בציון, בכיסוי ובספירות (`guru_score`, `result_counts`). **מיגרציה 0005**: 5 עמודות ל-`screener_snapshots` (`industry_pe`, `low_52`, `high_52`, `dividend_yield`, `industry_return_median`) + בנייה מחדש של `results` ו-`scores` (עלי-טבלאות; לא מפעיל cascade). `income_quarterly` ב-`DEFAULT_STATEMENTS` (בקשה רביעית למניה). חציון תשואה כוללת לענף מחושב ב-`jobs/universe.py` על כל ~5,600 מניות הסורק. ציון איכות = ממוצע 6 גורואים. API: `CriterionDoc.manual`, `API_VERSION` 12; frontend: תוויות, MANUAL.
- Verified: gate (ruff, 462 טסטים כולל גבולות באפט/נף, מיגרציה על DB עם נתונים) + `pnpm build`; חי על עותק DB: מיגרציה 0005 על 12 ריצות, ניתוח AAPL/KO/CRUS (באפט ונף מלאים, מומנטום מ-20 רבעונים אמיתיים); דפדפן headless: דשבורד, דף מניה (טאבים באפט/נף, שורות "בדיקה אנושית"), "איך זה מחושב", מובייל 390px בלי גלילה אופקית.
- NOT verified: **נף בהיקף** (ב-snapshots הישנים אין שדות/רבעונים: חציון תשואה כוללת, מועמדות עם נף); מיגרציה 0005 על ה-DB בשרת (תרוץ בפריסה; נבדקה על עותק של ה-DB המקומי); הורדת הרבעונים לכל המניות (~108 בקשות בריצה הראשונה); הגדרת `industryPe` של האתר.
- Traps / decisions: **כל הפרשנויות פתוחות** — `docs/formula-decisions.md` (B1–B8, N1–N7) ו-`docs/teacher-questions.md` (32 שאלות). B3 ו-B4 נכתבו כפתוחות לבקשת המפתח. מכפיל נף = טווח 0.4–0.6 (הוחלט). **להפעיל מחדש `serve`** (מיגרציה + API 12). עם באפט בלבד מועמדות 11→8 (CTSH, DHT, DINO, FSLR יצאו; NVDA נכנסה) על ריצה 12.
- Next: תשובות המורה; ריצה מלאה ולבדוק מועמדות עם נף; לאמת את `industryPe`.

## 2026-11-08 — כפתור "צור מחדש" לפרופיל החברה
- Changed: בכרטיס "על החברה" כפתור "צור מחדש" (עם אישור, כי זה עולה כסף ב-Gemini). `POST /api/profiles/{symbol}?force=true`, `refresh_profile(force=True)`: מדלג על בדיקת "עדכני", הטקסט החדש מוזרם לדף ("יחליף את התיאור הקודם בסיום") ושורת ה-DB מוחלפת (`ON CONFLICT … DO UPDATE`) רק כשהחדש הסתיים; כשל משאיר את הישן. `API_VERSION` 11 (שרת ישן יציג אזהרה במקום להתעלם מ-force). `SecClient` מקבל `today` לבדיקות.
- Verified: 401 טסטים (כולל: force מחליף שורה ולא מוסיף; כשל מוכרח משאיר את הישן); חי על עותק DB (CRUS): אישור, הזרמה, שורה אחת עם `created_at` חדש.
- Traps: **להפעיל מחדש `serve`** (API 11).

## 2026-11-08 — באג: פרופיל AEM מ-2013
- Cause: `SecClient.latest_annual_filing` חיפש רק 10-K/20-F ודילג על כל ה-40-F שהוגשו מאז 2014, ולכן בחר 20-F מ-28.03.2013. ה-`profiles` בשרת: רק AEM הייתה ישנה (שאר התאריכים 2025-11 עד 2026-10).
- Changed: `sources/sec.py`: הדוח השנתי החדש ביותר מכל סוג קובע; 40-F ⇒ `Unsupported` ("latest annual report is a 40-F"); דוח ישן מ-550 יום ⇒ `Unsupported`. 3 טסטים חדשים. נבדק חי מול SEC: AEM, KGC = 40-F (לא נתמך); TSM, DHT, AAON, CF, NTES תקינות.
- Data fix **לא בוצע**: שורת הפרופיל השגויה של AEM (filing_date 2013-03-28) עדיין בשרת — מנגנון ההרשאות חסם כתיבה לשרת מרוחק. למחוק: `DELETE FROM profiles WHERE symbol='AEM' AND filing_date='2013-03-28'` (פרופיל חדש לא ייווצר: 40-F לא נתמך).
- Next: תמיכה ב-40-F לפי זיהוי נספחים (ר' GOTCHAS).

## 2026-11-08 — ניתוח מניה בודדת: מ-~6 שנ' ל-~1–3 שנ'
- Measured: בשרת (ריצות adhoc 11–19) ניתוח לקח 5–6 שנ' גם בלי הורדת דוחות ו-13–18 שנ' לפני R6. הפירוק: בקשות הסורק 1.7 שנ' (503KB + 2.6MB) + **המתנה קבועה של 4 שנ' ביניהן** (`fetch_universe(pause=4.0)`, נועדה לסריקה המלאה) + ~1 שנ' דוחות.
- Changed: `jobs/adhoc.py`: `_recent_universe` — בלי המתנה, ורשימת המניות נשמרת בזיכרון 120 שנ' (ניתוח שני ברצף לא מושך שוב; חסימה לא נשמרת); הסריקה המלאה לא השתנתה. בדיקת סטטוס הניתוח בדף: כל 0.8 שנ' (היה 2).
- Verified: 396 טסטים; דפדפן headless על עותק DB מול האתר החי: לחיצה → טבלה: ORCL 2.7 שנ', CRM 1.0, NFLX 1.0.
- NOT verified: מהשרת ב-Railway (הפריסה תרוץ עם הדחיפה); הסתייגות: מחירים בניתוח שני ברצף עד 2 דקות ישנים.

## 2026-11-07 (לילה) — דף למידה: הסבר על כל דוח + זרימה לסימול חסר
- Changed: כרטיס "על הדוח" בכל לשונית (`frontend/src/learnIntro.ts`, בלי שינוי API); סימול בלי דוחות: כפתור "הורד את הדוחות והצג" באותו עמוד (`TickerAnalyzer` עם `forLearning`/`onDone`, בלי ניווט לעמוד המניה). הניתוח הזה סופר מול מגבלת הניתוחים היומית.
- Verified: `pnpm build`; דפדפן headless על עותק DB: הכרטיס, וסימול חדש (ADBE) → הורדה והצגה תוך 10 שנ' על אותו URL. סימול לא קיים נכשל עם הודעה (טסט קיים; לא נבדק חי).
- NOT verified: הטקסטים ב"על הדוח" לא נבדקו על ידי המפתח; הטענה על עמודת "12 חודשים אחרונים" במאזן (רבעון אחרון) מבוססת על ידע כללי ולא נבדקה מול נתוני האתר.

## 2026-11-07 (ערב) — E7 הזרמה, הסברים בקריטריונים, דף למידה, מטבע
- Changed: **E7:** תשובת Gemini מוזרמת לדף (`generate_stream`, טקסט חלקי בזיכרון השרת, `status` מחזיר `text`; נשמר ל-DB רק בסיום); פרומפט v1 (חישוב פשוט מותר רק ממספרים בדוח, מסומן "חישוב שלנו", בלי LaTeX). **"כל קריטריון מול הסף":** משפט הסבר מתחת לכל שורה + מתג (`analysis/meanings.py`). **דף למידה** `/learn/:symbol` (ר' ROADMAP L1). **מטבע:** `statement_fetches.currency` (מיגרציה **0004 תוספתית**), נקרא מ-"Financials in millions TWD". `API_VERSION` 8→10.
- Verified: gate (394 טסטים), `pnpm build`; E7 חי על עותק DB (CRUS: הטקסט הופיע אחרי ~28 שנ' והתמלא עד ~60 שנ'; בלי LaTeX אחרי תיקון); דפדפן headless: דף הלמידה (3 דוחות, 404, 390px) והקריטריונים (מתג).
- NOT verified: **מיגרציה 0004 על ה-DB בשרת** (תרוץ בפריסה; נבדקה על עותק עם נתונים); מטבע של TSM יופיע רק אחרי הורדה חדשה (בעותק בדקתי עם ערך ידני); ההסברים בדף הלמידה לא נבדקו על ידי המפתח; חברות פיננסיות/נדל"ן.
- Findings: **40-F** (KGC, AEM): המסמך הראשי הוא מעטפת ~375KB; AIF/MD&A/דוחות בנספחי EX-99.x והסדר שונה בין חברות; **20-F** (TSM, DHT): המסמך הראשי הוא הדוח כולו (ר' GOTCHAS). תמיכה ב-40-F לא נבנתה.
- Traps: מיגרציה 0004 → **`serve` מקומי ישן יסרב ל-DB חדש**, להפעיל מחדש. הסברי הלמידה מפתחים לפי התווית באנגלית של האתר; תווית חדשה בלי הסבר מפילה את `test_every_statement_line_seen_in_the_data_has_an_explanation`.
- Next: לאשר/לתקן הסברי הלמידה; 40-F לפי זיהוי נספחים; D8/D9 ואז F3.

## 2026-11-07 (אחה"צ) — E6 גרף, סגירת סעיפים, אימות R5 חי
- Changed: `EntryExitTimeline.tsx` (גרף עמודות לפי יום בדף "כניסות ויציאות": מעל הקו נכנסו, מתחת יצאו) ב-`HistoryPage`; ROADMAP: D13 אושר, F2/E4/C9/E6 נסגרו לפי תשובות המפתח. זיכרון: דחיפה כברירת מחדל.
- Verified: gate (384 טסטים, `pnpm build`); דפדפן headless על עותק DB: רוחב מלא ו-390px בלי גלילה אופקית (3 אירועי יציאה מ-06.11). **R5 חי בשרת (קריאה בלבד):** כל ההורדות מריצה 6 ואילך עם `report_date`, 952/952 צילומי סורק עם `last_report_date`; 51 הורדות ישנות (לפני R5) בלי תאריך — מטופלות ב"אימוץ".
- NOT verified: R5 על מחזור דיווח אמיתי; הגרף על נתוני שרת אמיתיים בכמה ימים.
- Skipped / deferred: **F3** (מחיקת `plans/v2-*`) — לא נעשה: ב-`v2-rebuild.md` §3 נמצאות נוסחאות הציון (D8/D9 שעוד לא אושרו) והערות בקוד מפנות אליו (`criteria.py`, `scoring.py`, `repo.py`). לעשות אחרי אישור D8/D9.
- Next: דף למידה (תוכנית + ויזואל לאישור), E7: KGC (40-F) והזרמת תשובה.
- Trap: `pkill -f "serve --port ..."` מתוך פקודה שמכילה את הטקסט הורג את ה-shell (שוב קרה) — לעצור לפי פורט (`ss -ltnp`).

## 2026-11-07 — R6: מהירות הורדה (ניסוי ב-Railway + מימוש)
- Changed: `probes/rate-limit/` (סקריפט ניסוי: עליית קצב בשלבים, עצירה בחסימה הראשונה, מדידת התאוששות). `jobs/refresh.py`: `download_statements` עם `Pacing.workers=4`, `pause=(0.5, 1.0)`; בלי הפסקות ארוכות (`rest_every`/`rest` הוסרו); הכתיבה ל-DB רק מה-thread הקורא; חסימה עוצרת בקשות חדשות, ממתינה `block_wait` וממשיכה מהנקודה (מונה "אירועי חסימה", לא בקשות).
- Verified: ניסוי ~4,500 בקשות, 0 חסימות (ר' ROADMAP "הושלם"); 384 טסטים, הטסטים של המקביליות 15 ריצות רצופות; טסטים ישנים של קצב/הפסקות עודכנו בכוונה (ההתנהגות השתנתה).
- NOT verified: ריצה אמיתית עם הקוד החדש; שימוש חוזר לאורך ימים; הפרויקט הריק `rate-probe-tmp` ב-Railway — מחיקה מה-CLI נתנה "not found" והוא עדיין ברשימה: למחוק מהדשבורד. קומיט `1699c98` נדחף ל-`v2` (הפריסה בשרת מתחילה ממנו).
- Traps: מחיקת פרויקט ב-Railway CLI לא מחזירה אישור; כתובת IP שונה בכל פריסה. `__data.json` — ר' GOTCHAS.
- Next: ריצה אמיתית ולהסתכל על הזמן וה-`blocked`; `__data.json` — הוחלט לא להחליף כרגע (ר' ROADMAP R6).

## 2026-11-06 (ערב) — R5: הורדה לפי `lastReportDate`
- Changed: מיגרציה **0003 תוספתית** (`screener_snapshots.last_report_date`, `statement_fetches.report_date`); הסורק מבקש `lastReportDate`; `jobs/refresh.py`: הורדה כשהתאריך בסורק חדש יותר ממה ששמור, תאריך ישן נשמר אם הדף עוד לא התעדכן (עד 3 ניסיונות), D18 כגיבוי, ריענון מלא כל **120** יום (היה 45), "אימוץ" הורדות ישנות שנעשו ≥3 ימים אחרי הדיווח; API `reports` ושורה בדף מניה ("הדוחות כוללים תקופה שנסגרה ב-…", ו"באתר כבר יש דוח…"). `API_VERSION` 7. תוכנית: `plans/report-date-detection.md`.
- Verified: 381 טסטים (גבולות: זהה/חדש/ישן יותר/חסר/דף שלא התעדכן/אימוץ/גיבוי; מיגרציה על DB עם נתונים); צילומי מסך headless על עותק DB: מצב "מאחור" ומצב "לא ידוע".
- NOT verified: **מחזור דיווח אמיתי** (האם הסורק והעמוד מתעדכנים באותו רגע; פיזור ההשהיה); מניות זרות; המיגרציה על ה-DB בשרת (תרוץ בפריסה).
- Traps: מיגרציה 0003 רצה בעליית התהליך; **`serve` מקומי ישן יסרב ל-DB חדש** (`SchemaTooNew`) — להפעיל מחדש. `test_adhoc` שבדק D18 פוצל.
- Next: פריסה (דחיפה) כשאין ריצה פעילה; אחרי הריצה הראשונה עם הקוד החדש לבדוק ב-DB שהורדות קיבלו `report_date`; R6 (האצת הורדה), R4 (תצוגה פתוחה).

## 2026-11-06 (אחה"צ) — פריסה ל-Railway, פרופילים רק בלחיצה
- Changed: **F2 (חלקי):** שירות `dashboard` ב-Railway (פרויקט `value-scanner`, ענף `v2`, Volume `dashboard-data` על `/data`, `DB_PATH=/data/value_scanner.db`, דומיין ציבורי, healthcheck `/api/health`); `probe` נמחק. Dockerfile: הוסר `VOLUME` (Railway דוחה אותו). **סריקה לא יוצרת עוד פרופילי חברה** (`pipeline.py`) — רק הכפתור "צור תיאור חברה" או `python -m value_scanner profiles` (החלטת המפתח; Gemini עולה כסף). `API_VERSION` 6. תיקון תצוגת "פירוט" באירועי כניסה/יציאה (RTL, `FilterChanges.tsx`). R4, R5 ב-ROADMAP.
- Verified: ריצה אמיתית מהשרת (ריצה 2, 288 דוחות, 0 חסימות, `ok` ב-33 דק'); האתר עונה, 401 בלי התחברות; טסט חדש נכשל על הקוד הישן ועובר על החדש.
- NOT verified: שהנתונים שורדים restart של הקונטיינר; כניסה עם הסיסמה (רק המפתח); קומיטים מקומיים **לא נדחפו** — כל דחיפה מפעילה פריסה שמפילה ריצה רצה.
- Traps: **פריסה באמצע ריצה = `interrupted`** (ההורדות נשמרות; ריצה חדשה ממשיכה, אבל אין ניתוח/מייל ואז 6 שעות המתנה). ריצה ראשונה בשרת מתחילה אוטומטית. `railway ssh` לא מעביר stdin (רק פקודה בשורת הפקודה). אל תריץ `pkill -f` עם טקסט שמופיע בפקודה עצמה.
- Next: דחיפה אחרי שאין ריצה פעילה; R5 (תוכנית ב-`plans/report-date-detection.md`); האצת הורדה (R6).

## 2026-11-06 (לילה) — **איבוד נתונים (באג שלי, שוחזר)**, E8, גרפים, מסנן
- **תקלה:** מיגרציה 0002 (בנייה מחדש של `runs`) הורצה ע"י `serve` ישן (המתזמן קורא `open_database` כל 15 דק' וקרא את קובץ המיגרציה החדש מהדיסק) עם המריץ הישן, מפתחות זרים דולקים: `DROP TABLE runs` מחק בשרשרת scores/results/snapshots/run_log/classifications/membership_events. **שוחזר** מעותק שנלקח שניות לפני (`var/value_scanner.db.wiped-backup` = המצב הריק, אפשר למחוק). `statement_*`, companies, profiles לא נפגעו.
- **מניעה:** `db._KNOWN_MIGRATIONS` נטען פעם אחת בעליית התהליך; קוד ישן מסרב ל-DB חדש ממנו (`SchemaTooNew`); טסטים (מיגרציה על DB עם נתונים; "תהליך ישן"). **כלל:** אחרי שינוי backend/מיגרציה — להפעיל מחדש `serve`; לא לכתוב מיגרציה הרסנית בלי בדיקה על DB עם נתונים.
- Changed: **E8 מומש** (ר' `plans/ticker-analysis.md`): `jobs/adhoc.py`, `POST /api/analyses`, `GET /api/analyses/{symbol}`, `POST /api/profiles/{symbol}`, `TickerAnalyzer` בחיפוש ובדף מניה לא מוכרת, "נותחו לפי טיקר". סרגל המסננים **מעל** המטריצה. גרפי דף המניה: שמות צירים, ספרות על הנקודות, ספי "מועמדת". ריחוף עשיר בגרף איכות/הזדמנות (רשימת המועמדות הוסרה). favicon, `ErrorBoundary`.
- Verified: 361 טסטים; AAPL מקצה לקצה בדפדפן headless (חיפוש → "נתח" → דף עם 28 קריטריונים); הדשבורד לא הושפע (ריצה 3, 106 מניות; ריצות adhoc לא ברשימת הריצות ולא ב-"הבאה").
- NOT verified: מניות זרות/פיננסיות בניתוח לפי טיקר; חסימת Cloudflare תחת שימוש חוזר; "צור תיאור חברה" מהכפתור (רק הפונקציה נבדקה); ה-`serve` שלך עדיין ישן — להפעיל מחדש.

## 2026-11-06 (ערב) — ריצה 2, E7, חיפוש, תוכנית E8
- Verified (ריצה 2, אמיתית): `ok` ב-81 שנ': 107 במעקב, 15 דוחות הורדו, **306 דולגו כטריים** (כללי D18 עובדים), אותן 11 מועמדות, VTMX בלי ציון. **אירוע כניסה/יציאה אמיתי ראשון:** NMIH יצאה (סיבה "דוחות": current ratio 2.03→1.75). המייל שנשלח הגיע (אישרת).
- Changed: **E7 נבנה** — `sources/sec.py`, `profile/gemini.py`, `jobs/profiles.py`, `python -m value_scanner profiles [סימולים]`, הסריקה מרעננת פרופילים למועמדות בלבד (רק כש-`GOOGLE_API_KEY` ו-`MY_EMAIL` מוגדרים; כשל לא מפיל ריצה), כרטיס "על החברה" בדף המניה. שדה החיפוש של הדשבורד עבר לשורה העליונה (מסנן גם גרף ומועמדות). `.claude/plans/ticker-analysis.md` — תוכנית E8 **לדיון, לא ממומש**.
- Verified (E7): 12 טסטים חדשים (קיצוץ פרקים, 20-F, כשל חילוץ, 402/503, רענון רק בדוח חדש, מפתח ב-header); חי: AAON (10-K, כולל נתוני מגזרים מה-MD&A) ו-DHT (20-F). **פרומפט v0** = הפרומפט מהבדיקה + סקטור/ענף + פסקת "מיקום בענף" — **לא סוכם איתך**. שגיאת תרגום ב-DHT: "הכנסות מספנות" במקום "הכנסות מהובלה"; פתיח "להלן פרופיל…" ו-`---` מיותרים.
- Verified (עוד פרופילים): RJF (פיננסית, 10-K), NBIX (פארמה, 10-K), DHT (20-F) נוצרו; KGC (40-F) = `unsupported` כמצופה. בדיקה אוטומטית של המספרים בפרופיל מול הפרקים שנשלחו: DHT 46/46, NBIX 61/68, RJF 32/41 מופיעים מילולית בדוח. **היתר חושבו ע"י המודל** (למשל צמיחה 21.5% = 2,860.5/2,355.3, ונתח הכנסות 72.4%) — בדקתי 2 ידנית והחשבון נכון, אבל זה עובר על הכלל "מספרים רק אם מופיעים בדוח"; **נושא לדיון בפרומפט**. לא נבדקה כל עובדה מול הדוח.
- NOT verified: Volume ושמירה אחרי restart בקונטיינר.
- Skipped (דורש אותך): E8 (שאלות 1–8 בתוכנית), נושאי `formula-decisions.md`, F2/F3, פרומפט E7.
- Traps: `run-local.sh` בשורש הוא קובץ שלך (לא מעקוב, לא נגעתי).
- **F1 הושלם:** `docker build` נכשל בהתחלה (pnpm חדש חוסם build של esbuild) ותוקן; הקונטיינר healthy, התחברות, אתר, וסריקה מוגבלת אמיתית עברו. הפעלתי Docker Desktop מ-WSL (`docker.exe`; בתוך WSL עצמו אין `docker`). קונטיינר הבדיקה שלי נמחק; `postgres_db` שעל המכונה אינו שלי ולא נגעתי.
- **דפדפן:** מעכשיו תמיד headless (נוסף ל-CLAUDE.md). ה-plugin של Playwright MCP מותקן בלי `--headless`, כלומר הוא נפתח headed — לשנות ב-config.
- Next: תשובות לתוכנית E8 ולפרומפט; F2/F3 (D13).

## 2026-11-06 — E1–E4, E6, C10, C9 (חלקי): דשבורד על נתוני אמת
- Changed: `api/schemas.py` + `api/views.py` (מודלי תגובה, `/api/criteria`, `/api/history`, ספירת עוברים לגורו), OpenAPI → טיפוסים (`frontend/src/api/`, טסט נכשל כשהסכמה ישנה), הגשת `frontend/dist` מ-FastAPI, frontend אמיתי (התחברות, דשבורד, דף מניה, ריצות+הגדרות+לוג, כניסות/יציאות, "איך זה מחושב"; ה-mock נמחק), `docs/criteria/opportunity.md`, `tools/compare_v1_v2.py` + `docs/c9-summary.md`, `python -m value_scanner test-alert`, Dockerfile עם שלב בניית frontend, `ARCHITECTURE.md` נכתב מחדש ל-v2. תיקוני באגים: חיבור SQLite עבר בין threads (500 על `/api/runs` ו-`/api/settings`), CSP חסם גופנים inline, logout לא חזר למסך ההתחברות.
- Verified: gate ירוק (334 טסטים) + `pnpm build`; בדפדפן (Playwright, על עותק DB של ריצה 1): כל המסכים, אור/כהה, מסך 390px בלי גלילה אופקית, התחברות שגויה/נכונה/יציאה, שמירת N ימים. מייל בדיקה נשלח ל-`MY_EMAIL` ב-SMTP האמיתי (השרת קיבל; **הגעה לתיבה לא נבדקה**).
- NOT verified: "הרץ כעת" ומתזמן אמיתי (לא לחצתי: היה מפעיל סריקה אמיתית); סטטוס חי בזמן ריצה; אירועי כניסה/יציאה אמיתיים (נבדק עם 2 אירועים סינתטיים); `docker build` (אין Docker ב-WSL); מועמדות מול האתר ידנית.
- Skipped (דורש אותך): ר' "שאלות שדורשות את ההחלטה שלך" ב-`docs/formula-decisions.md` (כינוי `Total Revenue` — VTMX ו-NMIH; סריקה משנית C3; גבולות C9) · E7 (הפרומפט לא סוכם, חיוב Gemini) · F1 (להפעיל WSL integration של Docker) · F2/F3 (D13 לא אושר; פריסה ל-Railway) · אישור טבלת הפרשנויות ב-`formula-decisions.md`.
- Traps / decisions: אל תריץ `pkill -f "value_scanner serve"` מתוך פקודת shell שמכילה את אותו טקסט (הורג את ה-shell); שרת פיתוח: `DASHBOARD_PASSWORD= DB_PATH=<עותק> serve` (משתנה ריק מנצח את `.env`). `tools/` חריג ל-E501.
- Next: תשובות לשאלות; ריצה שנייה (נותנת אירועי כניסה/יציאה אמיתיים); E7; F1–F3.

## 2026-11-06 — ריצה 1 הסתיימה + ניתוח סופי על נתוני אמת
- Verified: ריצה 1 `ok`: 5,601 מניות, 108 במעקב, 324/324 דוחות הורדו, 0 כשלונות, 0 חסימות, **35:54 דקות**. אחר כך `analyse_run` על המקור: 108 נותחו; 11 מועמדות (ZM, FSLR, MU, SKHY, DINO, GOOGL, CTSH, CRUS, KGC, LRN, DHT); VTMX בלי ציון איכות. כל 8 מסנני שיעור 3 עוברים ב-108/108 (פרט ל-NA: NMIH ו-VTMX בלי נתוני הכנסות/רווח; 11 פיננסיות ללא current ratio) — תואם לכך שהסורק עצמו בחר אותן.
- NOT verified: מייל אמיתי; מועמדות מול האתר/ידנית; ההחלטות ב-`docs/formula-decisions.md` ממתינות לאישור המפתח; VTMX (נדל"ן, חברה זרה) — למה אין לה דוחות (לא נבדק).
- Next: אישור המפתח לטבלת הפרשנויות; חיבור frontend; C9.

## 2026-11-06 — תיקון: חוב ארוך טווח לפי הכלל שלך + כלל עבודה
- Changed: ביטלתי את נוסחת התחליף שהמצאתי (Total Debt פחות חלק שוטף). כלל המפתח: אין שורת `Long-Term Debt` = אין חוב ארוך (0), כשהמאזן קיים; בלי מאזן = NA. `analysis/debt.py`, טסטים, `docs/criteria/*.md` עודכנו. נוסף `docs/formula-decisions.md` (כל הפרשנויות שמימשתי ועדיין ממתינות לאישור) וכלל ב-`CLAUDE.md`: לא להחליט נוסחאות שלא בסיכומים, ולהציג תקלה לפני שממשיכים.
- Verified: 326 טסטים ירוקים.
- NOT verified: הספירות על נתוני אמת אחרי השינוי (הניתוח הקודם הושפע מהנוסחה שבוטלה) — להריץ שוב.

## 2026-11-06 — ניתוח ראשון על נתוני אמת (עותק של ריצה 1, 92 מניות)
- Changed: (1) שלושת מסנני ה-5Y של שיעור 3 (צמיחת הכנסות, צמיחת EPS, ROE) משתמשים בערך של הסורק עצמו, ורק כגיבוי בחישוב מהדוחות; (2) `analysis/debt.py`: חוב ארוך טווח כש"Long-Term Debt" חסר = Total Debt פחות החלקים השוטפים (גראהם ופיוטרוסקי). טסטים עודכנו.
- Verified: gate ירוק (324). על עותק של ה-DB: 92 מניות נותחו; 10 מועמדות (CRUS, CTSH, DHT, DINO, FSLR, GOOGL, KGC, LRN, MU, SKHY); 0 בלי ציון איכות. **ממצא:** 15 מניות שהסורק אישר נכשלו/NA במסנני ה-5Y שלי (DINO: אצלי −2.4% מול +46.4% באתר) — חלון 5 השנים של האתר כולל שנים ישנות שהדוחות החינמיים מסתירים (`Upgrade`), ולי יש רק 5 FY. בשאר המסננים 0 כשלונות (שולי רווח, D/E, current ratio, שווי שוק, P/E).
- NOT verified: מספרים סופיים אחרי שני התיקונים (הניתוח הרץ לפני) — להריץ שוב; ריצה 1 עוד לא הסתיימה (294/324) ולא נותחה במקור; פיננסיות (11) מסומנות NA ב-current ratio לפי הספק 1; 65 NA ב-R&D הם לא-טק לפי D4; השוואה ידנית לאתר לדגימה.
- Next: להריץ `analyse_run` על ה-DB של ריצה 1 אחרי שתסתיים; C9.

## 2026-11-06 — מצב לוקאלי בלי סיסמה + תיקון serve
- Changed: בלי `DASHBOARD_PASSWORD` אין התחברות (מצב לוקאלי): מתקבלות רק בקשות עם Host של localhost/127.0.0.1/[::1] (הגנה מ-DNS rebinding), ו-`serve` מסרב להאזין על כתובת אחרת. `SESSION_SECRET` נדרש רק כשיש סיסמה. ה-CSRF header עדיין נדרש (טוקן קבוע `local-mode`). `cli.py`: `_serve()`.
- **תיקון לדיווח קודם:** ההערה "serve מפעיל את המתזמן" ב-E5 הייתה שגויה — ה-replace לא נכנס. עכשיו `_serve` מפעיל `start_scheduler` באמת.
- Verified: 319 טסטים ב-2.7 שניות; הרצה חיה על DB זמני: `/api/health` 200, `/api/runs` `[]`, Host זר = 403, `--host 0.0.0.0` בלי סיסמה נדחה.
- Traps / decisions: טסט שקורא `main(["serve"])` חייב לנתק `dotenv.load_dotenv`, אחרת קורא את ה-`.env` האמיתי ומפעיל שרת שלא נעצר (כך נתקעו הבדיקות). `serve` מסמן ריצות `running` כ-`interrupted` בעלייה — אל תפעיל אותו על `var/value_scanner.db` כשסריקה רצה.
- NOT verified: שהמתזמן באמת מפעיל ריצה אחרי 30 שניות (לא הרצתי בכוונה: ריצה אמיתית).

## 2026-11-05 — F1 (טיוטה, לא נבדקה): Dockerfile
- Changed: `Dockerfile` (python:3.11-slim + uv, `uv sync --frozen --no-dev`, בלי דפדפן; `DB_PATH=/data/value_scanner.db`; healthcheck על `/api/health`; `serve` על `$PORT`), `.dockerignore`.
- NOT verified: **`docker build`/`run` לא הורצו** — Docker Desktop לא מחובר ל-WSL (להפעיל WSL integration). ה-frontend לא נבנה לתוך התמונה ואין הגשת סטטיים מ-FastAPI. `playwright` עדיין בתלויות (v1) וגדל את התמונה; יוסר עם C9.
- Next: להפעיל WSL integration ולהריץ build; לחבר frontend.

## 2026-11-05 — E5 + "הרץ כעת" (backend)
- Changed: תלות `apscheduler` 3.x (D12). `jobs/scheduler.py`: `is_due` (עברו N ימים מהריצה המוצלחת האחרונה; אחרי ריצה שנכשלה/נחסמה ממתינים 6 שעות; אף פעם כשיש ריצה פעילה), `tick`, `run_now` (thread), `start_scheduler` (מסמן ריצות שנתקעו כ-`interrupted`, בדיקה כל 15 דק'). `POST /api/runs` (CSRF; 202 או 409). `serve` מפעיל את המתזמן. `settings.days_between_runs` נשמר ב-DB (ברירת מחדל 7).
- Verified: gate ירוק (310) עם שעון מזויף: גבולות N ימים, ההמתנה אחרי כשל, נעילה, 409.
- NOT verified: APScheduler באמת מפעיל את ה-job (נבדק רק `tick` ישירות); ריצה מתוזמנת אחת מלאה מעצמה (תנאי "Done" בתוכנית); סטטוס חי בדשבורד (רק polling של `/api/runs` קיים).
- Next: חיבור ה-frontend (E1-E4), Docker (F1).

## 2026-11-05 — E1 (backend): API לדשבורד
- Changed: תלויות (D12): `fastapi`, `uvicorn[standard]`, `itsdangerous`, `python-multipart`. `api/app.py` (`create_app`), `api/security.py` (סיסמה אחת ב-constant time, cookie חתום HttpOnly/SameSite=Lax/Secure מאחורי HTTPS, CSRF header על POST/PUT, הגבלת 5 כשלונות ל-15 דק', headers אבטחה), נקודות: `/api/auth/*`, `/api/stocks`, `/api/stocks/{symbol}`, `/api/runs`, `/api/runs/{id}/log`, `/api/settings`. שאילתות דשבורד ב-`Repository`. `python -m value_scanner serve`. נמחק מנגנון "not implemented".
- Verified: gate ירוק (299), כולל `tests/test_api.py` (401 בלי התחברות, 429, cookie, CSRF, טוקן מזויף, ולידציה, headers, נתוני ריצה).
- NOT verified: הרצה אמיתית של `serve` בדפדפן; `frontend/` (React) לא חובר ל-API ואין הגשת קבצים סטטיים; types מ-OpenAPI; "הרץ כעת" ותזמון (E4/E5); `DASHBOARD_PASSWORD`/`SESSION_SECRET` לא מוגדרים ב-`.env` (המפתח צריך להוסיף).
- Traps / decisions: ב-`api/app.py` אסור `from __future__ import annotations` (FastAPI לא מצליח לפתור dependencies מקומיים ומחזיר 422 במקום 401). חיבור לכל בקשה (SQLite לא בטוח בין threads).
- Next: E5 (APScheduler + נעילה), E4 (הרץ כעת), ואז חיבור ה-frontend.

## 2026-11-05 — C10 (חלקי): קובצי מסננים נוצרים מהקוד
- Changed: `analysis/docs.py`, `python -m value_scanner docs` → `docs/criteria/{screen,graham,fisher,piotroski}.md` (טבלה: מזהה, מבחן, נוסחה, סף, הערות + הסבר הציון), `tests/test_docs.py` נכשל אם הקבצים לא תואמים לקוד.
- NOT verified / חסר: `opportunity.md` (רכיבי ההזדמנות) ותצוגה בדשבורד ("איך זה מחושב" — E-phase); הנוסחאות באנגלית בכוונה (שמות השורות באתר); ללא ציון "סטייה מהשיעור" מפורש לכל מבחן.
- Next: אחרי שריצה 1 מסתיימת — `analyse_run` על ה-DB שלה ובדיקת דגימה.

## 2026-11-05 — C2, C7, C8 + חיבור לצינור
- Changed: `analysis/classify.py` (ברירות המחדל של `docs/classification-doubts.md`: tech/pharma/financial/cyclical לפי סקטור וענף בלבד; `pe_limit`, `rd_applies`, `pb_applies`), `analysis/scoring.py` (ציון גורו = ממוצע strength בלי NA + כיסוי, כיסוי <60% = לא מדורג; איכות = ממוצע גורואים, ≥2; הזדמנות = חציון 4 רכיבים; מועמדת: איכות ≥0.7 והזדמנות ≥0.2), `jobs/analyze.py` (`analyse_run`: סיווג+תוצאות+ציונים+רכיבים ל-DB; פיננסיות: 6 מבחנים לא רלוונטיים = NA), `run_scan` קורא לו אחרי ההורדה.
- Verified: gate ירוק (285 טסטים).
- NOT verified: על נתונים אמיתיים — ריצה 1 (`var/first-real-run.log`) התחילה לפני החיבור ולכן לא מנתחת; יש להריץ `analyse_run` על ה-DB שלה. C9 (השוואה ל-v1) לא נעשה. "מול ההיסטוריה" משתמש ב-`peRatio5Y` של הסורק (ממוצע, לא חציון כמו ב-D9). חציון P/B לסקטור דורש ≥3 מניות בריצה, אחרת מבחן פיוטרוסקי הראשון = NA.
- Traps / decisions: P/B שלילי או P/E שלילי לא נכנס להזדמנות (לא חל). חברה "regular" נשמרת בטבלת הסיווג כ-label בשם `regular`.
- Next: להריץ ניתוח על ריצה 1 ולבדוק דגימה ידנית מול האתר; C9; C10 (קובצי מסננים); אז E1 (אתר).

## 2026-11-05 — C6 (קוד): פיוטרוסקי (שיעור 6)
- Changed: `analysis/gurus/piotroski.py` — 8 בדיקות (FY אחרון מול הקודם): מכפיל הון מול חציון סקטור (D2: רק פיננסיות; NA בלי חציון), current ratio עלה, חוב ארוך/נכסים ירד, תזרים תפעולי חיובי וגדול מהרווח, ROA חיובי ועלה, פחות מניות, שולי גולמי עלו, מחזור נכסים עלה. `compare()` קיבל `lower_is_better`.
- Verified: gate ירוק (240). שוויון = FAIL; חסר שנה קודמת = NA; מכנה ≤0 = NA; חוב ארוך חסר נחשב 0 רק אם Total Debt=0.
- NOT verified: חיבור לסיווג/ציון, נתונים חיים. המכפיל ההוני ("20% מתחת לשוק או לענף") נקרא כ-P/B ≤ 0.8 × חציון הסקטור — פרשנות שלי; ר' ספקות בקובץ הספקות.
- Next: C2 סיווג (`pe_limit`, `cyclical`, `rd_applies`, `pb_applies`), C7 ציון, C8 הזדמנות; אחר כך חיבור לצינור (`run_scan` → results/scores) והשוואה ל-v1 (C9).

## 2026-11-05 — C5 (קוד): פישר (שיעור 5)
- Changed: `analysis/gurus/fisher.py` — 6 קריטריונים מה-PDF: P/S <0.8 (מחזוריות) / <1.5; צמיחת EPS = ממוצע 4 צמיחות שנתיות >15%; שולי רווח נקי ממוצע 5 שנים >5% (D1); התחייבויות/הון <0.4 (לפי דף הנוסחאות: סך ההתחייבויות); FCF למניה חיובי; שווי שוק / מו"פ בין 5 ל-15 כולל (רק טק/פארמה, אחרת NA — D4). `tests/test_fisher.py` (21).
- Verified: gate ירוק; גבולות בדיוק בסף, שלילי, חסר, NA כשבסיס צמיחה ≤0, הון עצמי ≤0 נכשל.
- NOT verified: על נתונים חיים; חריגי D3 (טק: P/E ו-P/OCF; תעשייה: P/E וגראהם; דרגת 0.4) **לא ממומשים** — רק הבסיס מה-PDF. `cyclical` ו-`rd_applies` נקבעים ע"י הסיווג (C2) שעוד לא קיים. הלשון "בין 5 ל-15" נקראה כטווח סגור (5 ≤ x ≤ 15).
- Next: C6 פיוטרוסקי, C2 סיווג, C7 ציון.

## 2026-11-05 — C4 (קוד): גראהם (שיעור 4)
- Changed: `analysis/gurus/graham.py` — 6 קריטריונים מה-PDF: מכירות >350M; current ratio >2; הון חוזר > חוב ארוך טווח; P/E <15 (פרמטר `pe_limit`, 25 לטק לפי D5/D6); P/E×P/B <22; צמיחת EPS >30% (ממוצע שנתיים אחרונות / ממוצע שנתיים ראשונות מתוך 5 FY, ובלי שנת הפסד). `evaluate()` מעגל ל-9 ספרות (רעש float בגבול). `tests/test_graham.py`.
- Verified: gate ירוק (199). גבולות: בדיוק בסף = FAIL; מכפיל ≤0 = FAIL (R4, לא PASS); שנת הפסד גוברת על נתון חסר; חסר = NA.
- NOT verified: על נתונים חיים; חיבור לסיווג (איזה `pe_limit` למי — C2/D6 עדיין לא); P12 (מטבע זר: סף 350M בלי המרה).
- Traps / decisions: אין שורת Long-Term Debt בחלק מהחברות (5/8 בדגימה). ללא שורה: Total Debt=0 → הון חוזר מול 0; הון חוזר > Total Debt → עובר; אחרת NA (ייתכן שהחוב קצר טווח). צמיחת EPS של גראהם שונה מצמיחת ה-5Y של הסורק/שיעור 3 (CAGR) — שתי הגדרות נפרדות בכוונה.
- Next: C5 פישר (שיעור 5), C6 פיוטרוסקי, C2 סיווג, ואז C7 ציון.

## 2026-11-05 — C3 (חלקי): הסינון הראשוני (שיעור 3)
- Changed: `analysis/rows.py` (שמות שורות חיים), `analysis/gurus/screen.py` (8 קריטריונים: שווי שוק ו-P/E מהסורק; צמיחת הכנסות ו-EPS כ-CAGR בין FY אחרון ל-4 שנים לפניו; שולי רווח NI/Revenue ב-TTM; D/E = Total Debt/Equity; current ratio; ROE ממוצע 5 שנים, ≥3 שנים תקפות), `tests/test_screen.py`.
- Verified: gate ירוק; טסטי גבולות (בדיוק בסף = FAIL כי ההשוואה חמורה), חסר = NA, שלילי, הון עצמי ≤0 = FAIL, בסיס צמיחה ≤0 = NA.
- NOT verified: מול נתונים חיים ומול הסינון של האתר (הסורק משתמש ב-5Y מדויק; לי יש רק 5 שנות FY = 4 מרווחים) — להשוות בריצת C9; הסינון המשני (ממוצעי 5 שנים של שולי רווח וצמיחה) לא ממומש; תמחור לפי Current (R1) מגיע מהסורק, לא מחושב.
- Traps / decisions: צמיחה "5Y" מחושבת כאן על 4 מרווחים בין 5 FY — ייתכן פער קל מול `revenueGrowth5Y` של האתר. D/E משתמש ב-`Total Debt` (כולל leases) כמו האתר, לא ב-`Long-Term Debt` (חסר ב-3 מתוך 8 חברות לדוגמה).
- Next: C2 סיווג, C4 גראהם (קריאת PDF שיעור 4).

## 2026-11-05 — C1 (חלקי): מודל קריטריון וטעינת דוחות
- Changed: `analysis/criteria.py` (`Status`, `Criterion`, `Result`, `strength`, `evaluate`, `compare`; NA לערך חסר/NaN), `analysis/statements.py` (`Statements.from_repo`: `fy(item, n)`, `ttm`, `current`, `series`; חסר = None, לא 0), `tests/test_criteria.py`.
- Verified: gate ירוק (165). גבולות strength: בדיוק 20% מעל = 1.0, מתחת ל-20% = 0.75, בסף (מחמיר) = 0.25, בדיוק 20% מתחת = 0.
- NOT verified: `thresholds.py` ו-`rows.py` (שמות שורות חיים) לא נכתבו — דורשים קריאת PDF השיעורים וביקורת מול נתוני ה-DB מהריצה המלאה. ריצה מלאה (`var/first-real-run.log`) רצה ברקע בעת הכתיבה.
- Next: לסיים את הריצה ולמדוד זמן (B4), אז `rows.py` מהשמות החיים, `thresholds.py`, C2.

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
