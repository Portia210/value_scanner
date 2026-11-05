<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# שיעור 3 - סינון ראשוני

| # | מזהה | מבחן | נוסחה | סף | הערות |
|---|---|---|---|---|---|
| 1 | `market_cap` | Market cap | market cap (screener, USD) | `> 2e+09` | — |
| 2 | `pe` | P/E | price / EPS (screener, current price) | `> 5` | lower bound only: a very low P/E is a warning sign (lesson 3) |
| 3 | `revenue_growth_5y` | Revenue growth, 5 years | CAGR of Revenue, latest FY vs 4 FYs earlier (%) | `> 0` | — |
| 4 | `profit_margin` | Net profit margin | Net Income / Revenue, current (TTM) (%) | `> 8` | — |
| 5 | `eps_growth_5y` | EPS growth, 5 years | CAGR of EPS (Diluted), latest FY vs 4 FYs earlier (%) | `> 0` | NA when the base year EPS is not positive |
| 6 | `debt_equity` | Debt / equity | Total Debt / Shareholders' Equity, current | `< 0.5` | equity <= 0 fails (debt with no owners' capital) |
| 7 | `current_ratio` | Current ratio | Total Current Assets / Total Current Liabilities, current | `> 2` | — |
| 8 | `roe_5y` | Return on equity, 5-year average | mean over FYs of Net Income / Shareholders' Equity (%), >= 3 valid years | `> 10` | years with equity <= 0 are skipped |

## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
