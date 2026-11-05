<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# שיעור 4 - בנג'מין גראהם

| # | מזהה | מבחן | נוסחה | סף | הערות |
|---|---|---|---|---|---|
| 1 | `sales` | Sales above $350M | Revenue, latest FY (millions) | `> 350` | reporting currency, not converted |
| 2 | `current_ratio` | Current ratio above 2 | Total Current Assets / Total Current Liabilities, current | `> 2` | — |
| 3 | `working_capital` | Working capital above long-term debt | (Total Current Assets - Total Current Liabilities) - Long-Term Debt, current | `> 0` | no Long-Term Debt row = no long-term debt (0), if the balance sheet exists |
| 4 | `pe` | P/E below 15 | price / EPS (screener, current) | `< 15` | P/E <= 0 fails; the limit is 25 for technology (D5) |
| 5 | `graham_number` | P/E x P/B below 22 | P/E x P/B (screener, current) | `< 22` | either factor <= 0 fails |
| 6 | `eps_growth` | EPS growth above 30%, no loss year | mean(EPS last 2 FY) / mean(EPS first 2 of 5 FY) - 1 (%); any FY EPS < 0 fails | `> 30` | needs 5 fiscal years of EPS |

## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
