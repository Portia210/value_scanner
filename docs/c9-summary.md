# סיכום C9 - השוואת v1 ל-v2 (מספרים בלבד)

נוצר ע"י `tools/compare_v1_v2.py`; הדוח המלא (עם סימולים וערכים) ב-`var/c9-comparison.md`, מחוץ ל-git.

השוואה לפי קריטריון על המניות שקיימות גם ב-v1 וגם ב-v2. **שימו לב:** v1 רץ על דוחות FY2024 ומחירי סוף שנה, v2 על FY2025/TTM ומחיר נוכחי, ולכן שינוי סטטוס אינו בהכרח הוכחה לשינוי לוגיקה.

מפתח: R1-R10 = ממצאי הביקורת (`.claude/plans/v2-audit.md`); F5-DE = v2 לפי דף הנוסחאות של שיעור 5 (סך התחייבויות / הון), v1 לפי Total Debt / Equity של האתר.

| תוצאה | כמות |
|---|---|
| DIFFERENT | 250 |
| NA in v2 | 99 |
| only in v1 (not in the lessons) | 156 |
| same | 899 |
| unmapped v1 check | 78 |

## שינויים לפי קריטריון ב-v1

| בדיקה ב-v1 | סוג | כמות |
|---|---|---|
| Debt-to-Equity | DIFFERENT | 34 |
| Debt-to-Equity | NA in v2 | 1 |
| EPS Growth | DIFFERENT | 33 |
| EPS Growth | NA in v2 | 3 |
| EPS growth | DIFFERENT | 26 |
| FCF/Share | DIFFERENT | 4 |
| FCF/Share | NA in v2 | 1 |
| Innovation Factor | DIFFERENT | 2 |
| Innovation Factor | NA in v2 | 55 |
| Net Profit Margin | DIFFERENT | 8 |
| Net Profit Margin | NA in v2 | 1 |
| P/E ratio | DIFFERENT | 22 |
| ROE | DIFFERENT | 12 |
| Valuation | DIFFERENT | 21 |
| Valuation | NA in v2 | 9 |
| current ratio | DIFFERENT | 2 |
| current ratio | NA in v2 | 9 |
| graham number | DIFFERENT | 66 |
| market cap | DIFFERENT | 2 |
| profit margin | DIFFERENT | 9 |
| profit margin | NA in v2 | 1 |
| revenue | DIFFERENT | 1 |
| revenue | NA in v2 | 1 |
| tech P/OCF check | UNMAPPED | 78 |
| working capital vs debt | DIFFERENT | 4 |
| working capital vs debt | NA in v2 | 9 |
| working capital vs long-term debt | DIFFERENT | 4 |
| working capital vs long-term debt | NA in v2 | 9 |

## שינויים שאין להם ממצא ביקורת מוכר (רק שינוי נתונים אפשרי)

- FCF/Share: 4
- revenue: 1
- working capital vs debt: 4
- working capital vs long-term debt: 4
