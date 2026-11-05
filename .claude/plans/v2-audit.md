# ביקורת קוד ותיעוד — לפני v2

**תאריך:** 2026-11-05 · **קומיט:** `a448e20` (master) + שינויים לא מקומטים ב-`reports_checks/ken_fisher_check.py` ו-`tests/`
**הנחת עבודה:** כל קוד ותיעוד חשודים עד שנבדקו מול המקור ומול הנתונים. הממצאים כאן נבדקו
בקריאת קוד מלאה ובהרצת סקריפטים על `data/` הקיים (140 מניות). כל ממצא מסומן איך אומת.

רמת חומרה: 🔴 משבש תוצאות / חוסם שרת · 🟠 סטייה מהשיעורים · 🟡 היגיינה / קוד מת.
הקובץ נמחק כשכל הממצאים טופלו (ROADMAP מפנה למזהים כאן).

---

## 1. איסוף נתונים (pipeline)

| # | חומרה | ממצא | מקום | אומת |
|---|---|---|---|---|
| P1 | 🔴 | **הנתונים אף פעם לא מתעדכנים.** ה-fetcher מדלג על כל דוח שקובץ ה-CSV שלו כבר קיים ("resume"), ואין שום מנגנון שמוחק אותו לפני ריצה חדשה. ריצה מתוזמנת לא תביא נתונים חדשים לאף מניה קיימת. | `pipeline/http_reports_fetcher.py:54` | קריאת קוד; `main.py` מוחק רק תיקיות של מניות שירדו מהרשימה |
| P2 | 🔴 | **לולאה אינסופית.** `while True` מנסה שוב כל 20 שניות כל עוד הקובץ לא נוצר. דף בלי טבלה, 404, או חסימת WAF → הריצה תקועה לנצח. | `pipeline/http_reports_fetcher.py:59-75` | קריאת קוד (`_fetch_single_report` חוזר בלי קובץ ב-non-200 וב-"no table") |
| P3 | 🔴 | **לולאה אינסופית בסורק.** `while True` עם `except` שבולע הכול; אם כפתור "Next" לא מופיע — לולאה לנצח. | `pipeline/get_filtered_companies.py:50-127` | קריאת קוד |
| P4 | 🔴 | **לא ירוץ על שרת:** `input()` אינטראקטיבי; Playwright עם `headless=False` בשלושה מקומות. | `main.py:118`, `main.py:30`, `pipeline/update_stock_list.py:29,38` | קריאת קוד |
| P5 | 🔴 | **קריטריוני הסינון הראשוני לא קיימים בקוד.** הסורק לוחץ "Filters" וקורא את מה שמוצג — כלומר הסינון שמור בחשבון StockAnalysis/בדפדפן, לא בקוד. אי אפשר לדעת או לשחזר אילו ספים הופעלו, ואם הם תואמים לשיעור 3. | `pipeline/get_filtered_companies.py:38-48` | **אומת מול צילום מסך מהמפתח (2026-11-05):** המסננים זהים לסינון הראשוני של שיעור 3. הסיכון שנשאר: שינוי בחשבון משנה את היקום בשקט → ר' D7 |
| P6 | 🟠 | **הסיווג רץ לפני הורדת הנתונים.** `generate_classification_csv()` (שלב 3) קורא `income.csv` מהריצה הקודמת; מניה חדשה מקבלת CAGR=None → מסווגת "Defensive" כברירת מחדל. | `main.py:132-139` | קריאת קוד |
| P7 | 🟠 | נתיבים יחסיים (`data/...`, `"cookies.txt"`, `rate_limit_debug.txt`) — תלוי בתיקייה שממנה מריצים. | `http_reports_fetcher.py:29,52,112`, `utils/get_symbol_csvs_paths.py:12` | קריאת קוד |
| P8 | 🟠 | שגיאות לכל מניה נבלעות ב-`logger.info` — אין סיכום כמה מניות נכשלו. | `pipeline/batch_processor.py:17` | קריאת קוד |
| P9 | 🟡 | זרימת login/בדיקת עוגייה כפולה (`main.ensure_valid_cookies` ו-`update_stock_list`). | `main.py:20`, `pipeline/update_stock_list.py:22-35` | קריאת קוד |
| P10 | 🟡 | `validate_cookie` בודק תוקף ה-`access_token` (קצר-מועד) — כנראה יגרום ל-login בכל ריצה. לא מזיק, אבל צריך לדעת. | `playwright_utils/cookie_utils.py:144-155` | קריאת קוד |
| P12 | 🔴 | **מטבע הדיווח של חברות זרות.** אצל ADR כמו ASR (מקסיקו) ו-ATAT (סין) הדוחות במטבע מקומי ושווי השוק בדולר. כל השוואה של סכום לסף בדולרים (הכנסות >350M$, שווי שוק/מו"פ) שגויה אצלן; מכפיל שמחושב ידנית יוצא שגוי ב-86–95%. המכפילים של האתר עצמם (P/E, P/S...) תקינים כי הם חסרי יחידות. | `benjamin_graham_check.py:57-63`, `ken_fisher_check.py:147-166` | סקריפט: השוואת מכפילים מחושבים מול האתר ל-140 מניות |
| P13 | 🟠 | **"חריגת קצב" היא בפועל אתגר Cloudflare** (`cf-mitigated: challenge`, דף "Just a moment"), לא 429 עם Retry-After. הקוד מתייחס לזה כ"אין טבלה" ויוצא בלי קובץ (→ P2). | `698c499:rate_limit_debug.txt` | קריאת ה-headers מההיסטוריה |
| P14 | 🔴 | **דוח רווח והפסד עבר כתובת.** `/financials/` הוא היום עמוד "Overview" בלי טבלת דוח; הדוח עצמו ב-`/financials/income-statement/`, ושולי רווח/FCF למניה עברו ל-`/financials/metrics/`. ה-fetcher הישן היה נתקע בלולאה האינסופית (P2) על כל מניה. | `pipeline/http_reports_fetcher.py:61-62` | probe מקומי + Railway, 2026-11-05: 10/10 `no_table` |
| P11 | 🟡 | כפילות מניה: `BRK.A` ו-`BRK.B` (אותה חברה, שתי סדרות). | `outputs/filtered_companies.json` | סקריפט |

## 2. בדיקות הגורואים (reports_checks)

| # | חומרה | ממצא | מקום | אומת |
|---|---|---|---|---|
| R1 | 🔴 | **התמחור מחושב לפי מחיר סוף שנת הכספים, לא המחיר הנוכחי.** כל המכפילים (P/E, P/B, P/S, P/OCF, שווי שוק) נלקחים מעמודת `FY 20XX` ולא מ-`Current`. 102 מתוך 140 מניות — המחיר הוא מסוף 2024. דוגמה AAON: P/E שנבדק 56.75 (FY2024) מול 64.38 (Current). שאלת "האם זול עכשיו" נענית במחיר ישן. | `benjamin_graham_check.py:41-92`, `ken_fisher_check.py:22-34` | סקריפט על `data/AAON/ratios.csv` |
| R2 | 🔴 | **גראהם: חסר כלל "אף שנה הפסדית".** שיעור 4 דורש צמיחת EPS >30% *וללא שנת הפסד*. הקוד בודק רק צמיחה. `BRK.A` ו-`BRK.B` עוברים את גראהם למרות שנת הפסד ב-5 השנים. | `formula_helpers.py:52-76` | סקריפט: 8 מניות עם שנת הפסד, 2 מהן PASS |
| R3 | 🔴 | **פישר: נוסחת צמיחת ה-EPS שגויה.** שיעור 5: ממוצע צמיחה שנתית (YoY) >15%. הקוד: צמיחה מצטברת של ממוצע שנתיים ראשונות מול אחרונות ≥15% — כלומר 15% לכל התקופה במקום לשנה. 22 מניות עוברות בקוד ונכשלות לפי השיעור (AMAT: 24.8% בקוד מול 8.0% שנתי). | `ken_fisher_check.py:118` | סקריפט |
| R4 | 🔴 | **מכפיל שלילי עובר.** `pe_ratio < 40 if pe_ratio else False` — P/E שלילי (חברה מפסידה) הוא truthy ו-<40 → PASS. אותו דבר ל-P/OCF ולחריג התעשייה. כרגע אין מקרה בנתונים, אבל זה יקרה. | `ken_fisher_check.py:56-57,64` | קריאת קוד; סקריפט (0 מקרים כרגע) |
| R5 | 🟠 | **82% מהמניות נבדקות כ"טכנולוגיה".** כל מה שמסווג Cyclical או High Growth מקבל `valuation_method="P/OCF"`, ובגראהם זה מפעיל את חריג הטכנולוגיה (P/E עד 25 + P/OCF<P/E, בלי מכפיל גראהם). 115/140 מניות, כולל כל 28 מניות התעשייה. בשיעורים החריג הוא לטכנולוגיה בלבד, ולתעשייה דווקא מכפיל גראהם. | `company_classifiers/main.py:76,108,121,129`, `benjamin_graham_check.py:35-36` | סקריפט על `company_classifications.csv` |
| R6 | 🟠 | פישר: שולי רווח נבדקים לשנה האחרונה בלבד; השיעור דורש ממוצע 5 שנים. | `ken_fisher_check.py:105` | קריאת קוד |
| R7 | 🟠 | פישר: חברה **בלי** נתוני מו"פ עוברת אוטומטית, וחברה עם מו"פ קטן נכשלת. צריך N/A (לא נספר), לא PASS. | `ken_fisher_check.py:156-160` | קריאת קוד |
| R8 | 🟠 | פישר: ספי טכנולוגיה P/OCF<25, P/E<40 — לא מופיעים בשיעורים (שם: P/E<25, P/OCF<P/E). | `ken_fisher_check.py:55-59` | השוואה לשיעור 5 + הסיכום |
| R9 | 🟠 | פישר תעשייה: `P/E<25 **או** מכפיל גראהם` — "או" מקל מאוד; מכפיל גראהם 22.5 כאן מול 22 בבדיקת גראהם. | `ken_fisher_check.py:73-74` | קריאת קוד |
| R10 | 🟠 | בדיקה בסיסית: רווח נקי נבדק כ"מגמה" (ממוצע אחרון > ממוצע ראשון), השיעור דורש רווח חיובי כמעט בכל שנה. ROE סף 15% (השיעור: 10% בסינון ראשוני, 15% אצל באפט). תנאי "שולי רווח תפעולי >0" לא מופיע בשיעורים. | `basic_reports_check.py:14-55` | השוואה לשיעור 3 |
| R11 | 🟠 | חסרים לגמרי: D/E<0.5, צמיחת הכנסות 5Y>0, צמיחת EPS 5Y>0, P/E>5 מהסינון הראשוני (כנראה הונחו כמסוננים בסורק — ר' P5). כל פיוטרוסקי (שיעור 6) לא קיים. | — | השוואה לשיעורים 3, 6 |
| R12 | 🟠 | צמיחה עם בסיס שלילי: חלוקה בממוצע שלילי הופכת סימן. לא קורה כרגע בנתונים. | `formula_helpers.py:38-45` | סקריפט (0 מקרים) |
| R13 | 🟡 | התוצאה בינארית לכל גורו (`all()`); לא נשמר ערך/סף/מרחק לכל קריטריון — לא ניתן לדרג. הבוליאנים נגזרים מחיפוש `"True"` בתוך מחרוזת ההודעה. | `basic_reports_check.py:73-76` | קריאת קוד |

## 3. סיווג חברות

| # | חומרה | ממצא | מקום | אומת |
|---|---|---|---|---|
| K1 | 🟠 | `Financials` מופיע גם ב-`CYCLICAL_SECTORS` וגם ב-`DEFENSIVE_SECTORS`; בפועל מנצח הדפנסיבי כי נבדק קודם. סתירה בקבועים. | `constants/sectors.py:26,59` | קריאת קוד |
| K2 | 🟡 | `Semiconductors` ברשימה המחזורית אף פעם לא חל (סקטור Technology נתפס קודם). | `constants/sectors.py:45` | קריאת קוד |
| K3 | 🟡 | `Medical Instruments & Supplies`, `Health Information Services` מסווגים "פארמה" — החלטה, לא בהכרח שגיאה. | `constants/sectors.py:16-17` | — |

## 4. קוד מת ושבור

| # | חומרה | ממצא | מקום |
|---|---|---|---|
| X1 | 🟡 | `pipeline/reports_fetcher.py` — fetcher ישן מבוסס Playwright, לא בשימוש. | |
| X2 | 🟡 | `reports_checks/cyclical_classifier.py` — מסווג AI (langchain/OpenAI), לא בשימוש. גורר את תלויות langchain. | |
| X3 | 🟡 | `utils/linear_regression.py` קורא ל-`parse_row_percentages` שלא קיימת → NameError. לא בשימוש. | אומת ב-import |
| X4 | 🟡 | `utils/enum_generator.py:7-9` — `if not exists: os.remove()` → קורס ב-import אם התיקייה חסרה (תנאי הפוך). | |
| X5 | 🟡 | `playwright_utils/page_helper.py`, `quick_actions.py` — בשימוש רק ע"י X1. | grep |
| X6 | 🟡 | `test_cleanup.py` — סקריפט ידני, לא טסט. `testing_scripts/*.ipynb` — מחברות ניסוי. | |
| X7 | 🟡 | `utils/pd_helpers.py` מייבא Playwright — קוד הניתוח תלוי בספריית דפדפן. | |
| X8 | 🟡 | תלויות לא בשימוש ב-`pyproject.toml`: langchain ×3, jupyter, ipykernel, ipython, scipy (רק X3); `dotenv` וגם `python-dotenv`. אין pytest. | |
| X9 | 🟡 | קבצים מיוצרים מקומטים ל-git: `outputs/*`, `rate_limit_debug.txt`, `short_report.md`. **הריפו ציבורי** ב-GitHub. נבדק: אין עוגיות ב-`rate_limit_debug.txt`, ו-`.env`/`cookies.txt` לא נמצאים בהיסטוריה. | `gh repo view`, `git log --all` |

## 5. תיעוד שגוי

| # | ממצא |
|---|---|
| T1 | `CLAUDE.md` מתאר "ספריית Playwright utilities" עם `utils/browser_manager.py`, `page_helper.py` וכו'. בפועל הקבצים ב-`playwright_utils/`, והפרויקט הוא סורק מניות. כל הקובץ לא רלוונטי. |
| T2 | `PROJECT_OVERVIEW.md`: "Tech/Growth: P/OCF<25, P/E<40" מיוחס לגראהם — בפועל אלה ספי פישר; גראהם-טק = P/E 5–25 + P/OCF<P/E. "Tech/Pharma → Tech/Growth" — שם הסוג בקוד הוא `Tech/Pharma`. "Innovation R&D>10% (Tech only)" — בקוד הנוכחי (לא מקומט) זה הפוך: טק = P/R&D 5–15, אחרים = R&D/Rev>10%. |
| T3 | Docstring של `benjamin_graham_check` מונה 5 קריטריונים; בפועל 6–7 והרכבם תלוי בסיווג. |

## 6. מה עובד ונשמר
- פירוק ה-HTML וניקוי הטבלאות (`df_cleaner`, `parse_html_table_str`) — עובד על 140 מניות, 5 שנות FY לכל אחת.
- ה-rate limiting (הפסקה כל 10 בקשות, 60 שניות על 429) — נשמר כרעיון.
- עוגיות → httpx במקום דפדפן לכל דוח — מהיר ונכון.
- `tests/verify_innovation_logic.py` — 5 טסטים עוברים (`uv run python -m unittest tests.verify_innovation_logic`).
- נתוני `Free Cash Flow Per Share` קיימים ב-`income.csv` של 139/140 מניות.
