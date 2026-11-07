<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# שיעור 6 - יוסף פיוטרוסקי

| # | מזהה | מבחן | נוסחה | סף | הערות |
|---|---|---|---|---|---|
| 1 | `current_ratio` | Current ratio improved | Total Current Assets / Total Current Liabilities: FY0 > FY1 | `> 0` | — |
| 2 | `lt_debt_assets` | Long-term debt / assets fell | Long-Term Debt / Total Assets: FY0 < FY1 | `> 0` | no Long-Term Debt row = no long-term debt (0), if the balance sheet exists |
| 3 | `cash_flow` | Operating cash flow positive and above net income | Operating Cash Flow > 0 and > Net Income, FY0 | `> 0` | — |
| 4 | `roa` | Return on assets positive and higher | Net Income / Total Assets: FY0 > 0 and FY0 > FY1 | `> 0` | — |
| 5 | `shares` | Fewer shares outstanding | Shares Outstanding (Diluted): FY0 < FY1 | `> 0` | reported in millions, so a small buyback can round to equal (= fail) |
| 6 | `gross_margin` | Gross margin improved | Gross Profit / Revenue: FY0 > FY1 | `> 0` | — |
| 7 | `asset_turnover` | Asset turnover improved | Revenue / Total Assets: FY0 > FY1 | `> 0` | — |

## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- שורה `MANUAL` ("בדיקה אנושית") אי אפשר לחשב מהדוחות: היא בטבלה, ואינה נספרת בציון או בכיסוי.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
