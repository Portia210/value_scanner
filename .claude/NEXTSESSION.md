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

## 2026-11-05 — ביקורת ותוכנית v2
- Changed: הועתקו קבצי ה-docs מהתבנית; נכתבו `plans/v2-audit.md`, `plans/v2-rebuild.md`, ROADMAP, ARCHITECTURE (מצב קיים), GOTCHAS; `CLAUDE.md` נכתב מחדש; ל-`PROJECT_OVERVIEW.md` נוספה אזהרה שהוא לא מדויק. **אין שינוי בקוד.**
- Verified: קריאת כל קובצי ה-Python; סקריפטים על 140 המניות ב-`data/` אישרו את R1, R2, R3, R5, P11; `tests/verify_innovation_logic.py` עובר (5 טסטים); אין `.env`/`cookies.txt` בהיסטוריית git; הריפו ציבורי.
- NOT verified: מה הסינון השמור בחשבון StockAnalysis (P5); האם login headless עובד; זמן ריצה מלאה; התנהגות מ-IP של Railway.
- Traps / decisions: המפתח בחר ארכיטקטורה A (שירות אחד, FastAPI + APScheduler + SQLite על Volume). המפתח נתן הרשאה מלאה לשנות מבנה ולערוך כל קובץ. השינויים הלא מקומטים ב-`ken_fisher_check.py` ו-`tests/` שייכים למפתח — לא לגעת לפני D0.
- Next: המפתח עובר על התוכנית ועל החלטות D0–D15 ב-ROADMAP; אחרי אישור מתחילים ב-A1.
