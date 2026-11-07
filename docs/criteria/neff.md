<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# שיעור 8 - ג'ון נף

| # | מזהה | מבחן | נוסחה | סף | הערות |
|---|---|---|---|---|---|
| 1 | `pe_vs_industry` | P/E 40%-60% below the industry's | P/E / industry P/E, a band 0.4 .. 0.6 (screener, current) | `>= 0.4` | a band, both ends included (decided 2026-11-07); P/E <= 0 fails; no industry P/E = NA |
| 2 | `price_in_range` | Price in the lower half of the 52-week range | (price - 52-week low) / (52-week high - 52-week low) | `< 0.5` | below the middle of the range, as in the summary (N2); shows the multiple is low because the price fell |
| 3 | `eps_growth` | EPS growth between 7% and 22% | EPS growth over 5 years (%): the screener's figure, else CAGR of EPS (Diluted) | `>= 7` | a band 7 .. 22, both ends included; too much growth is as suspect as too little (N3) |
| 4 | `total_return` | Total return twice the industry's | (EPS growth + dividend yield) / P/E  >=  2 x the industry median of the same figure | `>= 2` | value = the stock's figure, threshold = 2 x industry median (N4); the median is over all screener stocks of the industry with a positive P/E (at least 5) |
| 5 | `revenue_vs_eps` | Revenue growth at least 70% of EPS growth | Revenue growth / EPS growth, both over 5 years (%) | `>= 0.7` | organic growth; NA when EPS growth <= 0 (N5) |
| 6 | `fcf_per_share` | Free cash flow per share positive | Free Cash Flow Per Share, current (TTM, else latest FY) > 0 | `> 0` | the same test as lesson 5 |
| 7 | `momentum` | Each of the last 4 quarters above the same quarter a year earlier | EPS (Diluted) of each of the 4 latest fiscal quarters > EPS of the same quarter one year before | `>= 4` | value = quarters that improved; each quarter on its own, as the summary says (N8) |

## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- שורה `MANUAL` ("בדיקה אנושית") אי אפשר לחשב מהדוחות: היא בטבלה, ואינה נספרת בציון או בכיסוי.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
