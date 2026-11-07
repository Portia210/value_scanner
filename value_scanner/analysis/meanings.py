"""One plain-Hebrew sentence per criterion: what it measures (shown under its row on the stock page).

Wording follows the developer's concepts bank (`בנק-מושגים.md`); it says what the figure *is*, not
how the formula is built (that is `Criterion.formula`) and adds no rule the lessons do not state.
A test checks that every criterion has one.
"""

# ruff: noqa: E501  (long Hebrew sentences)
from __future__ import annotations

MEANINGS: dict[tuple[str, str], str] = {
    # lesson 3 - initial screen
    ("screen", "market_cap"): "השווי שהשוק מייחס לחברה כרגע: מחיר המניה כפול מספר המניות.",
    ("screen", "pe"): "מחיר המניה ביחס לרווח למניה. מדד לזוֹלוּת החברה.",
    ("screen", "revenue_growth_5y"): "הקצב השנתי הממוצע שבו ההכנסות גדלו ב-5 השנים האחרונות.",
    ("screen", "profit_margin"): "כמה מכל דולר הכנסות נשאר כרווח נקי (ב-12 החודשים האחרונים).",
    ("screen", "eps_growth_5y"): "הקצב השנתי הממוצע שבו הרווח למניה גדל ב-5 השנים האחרונות.",
    (
        "screen",
        "debt_equity",
    ): "היחס בין החוב להון העצמי, מדד הסיכון המרכזי בהשקעות ערך. נמוך יותר = פחות סיכון.",
    (
        "screen",
        "current_ratio",
    ): "היכולת של החברה לכסות את ההתחייבויות שלה לשנה הקרובה (נכסים שוטפים מול התחייבויות שוטפות).",
    (
        "screen",
        "roe_5y",
    ): "כמה רווח החברה מייצרת לבעלי המניות ביחס להון העצמי שלהם, בממוצע של 5 שנים.",
    # lesson 4 - Graham
    ("graham", "sales"): "גודל העסק: ההכנסות בשנת הכספים האחרונה.",
    (
        "graham",
        "current_ratio",
    ): "היכולת של החברה לכסות את ההתחייבויות שלה לשנה הקרובה (נכסים שוטפים מול התחייבויות שוטפות).",
    (
        "graham",
        "working_capital",
    ): "האם נכסים שוטפים פחות התחייבויות שוטפות מכסים את החוב לטווח ארוך.",
    ("graham", "pe"): "מחיר המניה ביחס לרווח למניה. מדד לזוֹלוּת; הסף משתנה לפי סוג החברה.",
    ("graham", "graham_number"): "מכפיל הרווח כפול מכפיל ההון: מדד תמחור אחד שמאזן בין השניים.",
    (
        "graham",
        "eps_growth",
    ): "כמה הרווח למניה גדל בין תחילת התקופה לסופה (ממוצע שנתיים אחרונות מול שנתיים ראשונות), בלי שנת הפסד.",
    # lesson 5 - Fisher
    ("fisher", "ps"): "שווי השוק ביחס להכנסות. נחשב פחות נתון למניפולציה חשבונאית ממכפיל הרווח.",
    ("fisher", "eps_growth"): "הצמיחה השנתית הממוצעת של הרווח למניה, כממוצע של 4 צמיחות שנתיות.",
    ("fisher", "net_margin"): "כמה מכל דולר הכנסות נשאר כרווח נקי, בממוצע של 5 שנים.",
    ("fisher", "debt_equity"): "סך ההתחייבויות ביחס להון העצמי.",
    ("fisher", "fcf"): "האם החברה מייצרת בפועל כסף פנוי לכל מניה (תזרים חופשי למניה).",
    (
        "fisher",
        "rd",
    ): 'גודל ההשקעה במחקר ופיתוח ביחס לגודל החברה (שווי שוק חלקי מו"פ). רלוונטי בעיקר לטכנולוגיה ופארמה.',
    # lesson 6 - Piotroski (this year against last year)
    (
        "piotroski",
        "pb_discount",
    ): "האם המניה נסחרת בזול ביחס להון העצמי שלה לעומת חציון הסקטור (חברות פיננסיות בלבד).",
    (
        "piotroski",
        "current_ratio",
    ): "האם היכולת לכסות התחייבויות לטווח קצר השתפרה לעומת השנה הקודמת.",
    ("piotroski", "lt_debt_assets"): "האם החוב לטווח ארוך ביחס לנכסים ירד לעומת השנה הקודמת.",
    (
        "piotroski",
        "cash_flow",
    ): 'האם החברה מייצרת מזומן מפעילות שוטפת, ויותר מהרווח הנקי (בדיקה שהרווח אינו רק "על הנייר").',
    ("piotroski", "roa"): "האם החברה מרוויחה על הנכסים שלה, ויותר מהשנה הקודמת.",
    ("piotroski", "shares"): "האם מספר המניות ירד (רכישה עצמית) ולא עלה (גיוס הון).",
    ("piotroski", "gross_margin"): "האם שולי הרווח הגולמי השתפרו לעומת השנה הקודמת.",
    (
        "piotroski",
        "asset_turnover",
    ): "האם החברה מייצרת יותר הכנסות מכל דולר נכסים לעומת השנה הקודמת.",
}


def meaning(guru: str, criterion_id: str) -> str:
    return MEANINGS.get((guru, criterion_id), "")
