<!-- נוצר אוטומטית מ-value_scanner/analysis/gurus/*.py: python -m value_scanner docs. לא לערוך ידנית. -->

# הזדמנות קנייה (מרווח ביטחון)

לכל מניה ארבעה רכיבים אפשריים, כולם במחיר הנוכחי. רכיב שאינו חל על המניה אינו נספר.

| מזהה | רכיב | נוסחה |
|---|---|---|
| `graham_number` | Graham number | 1 - sqrt(P/E x P/B / 22.5)  (not technology; P/E and P/B positive) |
| `fair_pe` | Fair P/E | 1 - P/E / fair P/E  (fair P/E 15, technology 25; P/E positive) |
| `vs_history` | Versus its own history | 1 - P/E / 5-year P/E  (the screener's 5-year average P/E; both positive) |
| `price_sales` | Price to sales | 1 - P/S / limit  (limit 0.8 cyclical, 1.5 other; not technology; P/S positive) |

## איך זה נכנס לציון

- ציון ההזדמנות הוא **החציון** של הרכיבים שחלים על המניה (אין רכיב שחל = אין ציון).
- מועמדת לקנייה: איכות ≥ 0.7 **וגם** הזדמנות ≥ 0.2.
- איכות = ממוצע ציוני הגורואים שדורגו (לפחות שניים); גורו עם כיסוי מתחת ל-60% אינו מדרג.
