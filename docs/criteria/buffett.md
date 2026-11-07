<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# שיעור 7 - וורן באפט

| # | מזהה | מבחן | נוסחה | סף | הערות |
|---|---|---|---|---|---|
| 1 | `consumer_monopoly` | Position: a consumer monopoly | Could someone with billions and the best managers build a competitor? Brand, patents, must-have product, essential service (lesson 7) | `בדיקה אנושית` | a person decides; not part of any score |
| 2 | `inflation_pricing` | Can raise prices with inflation | Did the product price rise over one or two decades without losing market share? | `בדיקה אנושית` | a person decides; not part of any score |
| 3 | `simple_product` | Simple product and business model | Is the product easy to understand, with a clear business model? | `בדיקה אנושית` | a person decides; not part of any score |
| 4 | `eps_growth` | EPS grew every year, no loss year | EPS (Diluted) higher than the year before in each step over 5 FY (4 steps), and Net Income > 0 in all 5 FY | `>= 4` | value = number of yearly increases; NA with fewer than 5 fiscal years (B1) |
| 5 | `earnings_vs_liabilities` | 5-year net income above long-term liabilities | sum of Net Income over 5 FY > Total Liabilities - Total Current Liabilities (latest FY) | `> 0` | long-term liabilities is a derived figure, not a row of the site (B2); threshold = the liabilities; not applicable to financial companies |
| 6 | `roe_5y` | Return on equity, 5-year average | mean over FYs of Net Income / Shareholders' Equity (%), >= 3 valid years | `> 15` | the same figure as lesson 3 with a stricter threshold (15% instead of 10%) |
| 7 | `roa` | Return on assets, last year | Net Income / Total Assets, latest FY (%) | `> 12` | a high bar (B5); on year-end assets |
| 8 | `retained_earnings` | Earnings growth relative to retained earnings | (Net Income FY0 - Net Income FY1) / Retained Earnings FY0 (%) | `>= 12` | OPEN (B3): one-year change, as the PDF says; retained earnings <= 0 fails |
| 9 | `fcf` | Free cash flow positive, last year | Free Cash Flow, latest FY > 0 | `> 0` | OPEN (B4): last year, as the PDF says (the summary says a 5-year average) |
| 10 | `dcf_price` | Attractive price by DCF | Buffett prices a company only by discounted cash flow; the lesson gives no discount rate, horizon or terminal value | `בדיקה אנושית` | a person decides; not part of any score |

## איך זה נכנס לציון

- כל קריטריון מחזיר `PASS` / `FAIL` / `NA` ועוצמה (strength) בין 0 ל-1: עובר עם מרווח של לפחות
  20% מהסף = 1.0; עובר בפחות = 0.75; נכשל בפחות מ-20% = 0.25; נכשל בהרבה = 0.
- שורה `MANUAL` ("בדיקה אנושית") אי אפשר לחשב מהדוחות: היא בטבלה, ואינה נספרת בציון או בכיסוי.
- נתון חסר = `NA`: לא נספר בציון, ומוריד את ה"כיסוי". כיסוי מתחת ל-60% = הגורו לא מדרג את המניה.
- בדיוק על הסף נכשלים (השוואה חמורה) אלא אם כתוב אחרת. ערך שלילי לא עובר מבחן "מתחת לסף".
