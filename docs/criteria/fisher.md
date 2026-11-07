<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# שיעור 5 - קן פישר

| # | מזהה | מבחן | נוסחה | סף | הערות |
|---|---|---|---|---|---|
| 1 | `ps` | Price / sales | P/S (screener, current) | `< 1.5` | limit 0.8 for cyclical companies, 1.5 otherwise; P/S <= 0 fails |
| 2 | `eps_growth` | EPS growth, 5-year average | mean of the 4 year-over-year growths of EPS (Diluted) over 5 FY (%) | `> 15` | NA if any year's base EPS is not positive |
| 3 | `net_margin` | Net margin, 5-year average | mean over FYs of Net Income / Revenue (%), >= 3 valid years | `> 5` | D1: 5% (PDF) rather than the 8%/15% sector variant |
| 4 | `debt_equity` | Liabilities / equity | Total Liabilities / Shareholders' Equity, current | `< 0.4` | equity <= 0 fails. Lesson 5's formula sheet says total liabilities |
| 5 | `fcf` | Positive free cash flow per share | Free Cash Flow per share, current | `> 0` | — |
| 6 | `rd` | Market cap / R&D between 5 and 15 | market cap (USD millions) / Research & Development, latest FY | `>= 5` | band: 5 <= ratio <= 15. Technology and pharma only; NA elsewhere (D4) |

## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- שורה `MANUAL` ("בדיקה אנושית") אי אפשר לחשב מהדוחות: היא בטבלה, ואינה נספרת בציון או בכיסוי.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
