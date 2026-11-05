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
