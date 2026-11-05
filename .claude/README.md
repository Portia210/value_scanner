# תבנית Claude Code — מדריך למפתח

> הקובץ הזה מיועד לך ולא ל-Claude. רק `CLAUDE.md` נטען אוטומטית, אז הקובץ הזה לא
> צורך קונטקסט. פרטים טכניים משתנים בין גרסאות: [תיעוד Claude Code](https://docs.claude.com/en/docs/claude-code/overview).

## מה יש בתבנית

| קובץ / תיקייה | תפקיד | נטען מתי |
|---|---|---|
| `CLAUDE.md` | עובדות הפרויקט וכללי עבודה. רזה בכוונה | תמיד |
| `.claude/skills/*` | נהלים מפורטים: bootstrap, אבטחה, מיגרציות, דיבוג, תלויות | רק כשהמשימה רלוונטית |
| `.claude/commands/` | `/gate` ו-`/finish` | כשאתה מפעיל |
| `.claude/agents/code-reviewer.md` | סוקר diff בקונטקסט נפרד | לפני commit |
| `.claude/hooks/` | אכיפה: חסימות, הקשר בפתיחת סשן, פורמט אוטומטי | אוטומטית |
| `.claude/settings.json` | הרשאות (allow / ask / deny) ורישום ה-hooks | אוטומטית |
| `NEXTSESSION` / `ROADMAP` / `ARCHITECTURE` / `GOTCHAS` | זיכרון הפרויקט | לפי הצורך |
| `.gitignore`, `.gitattributes`, `.editorconfig`, `.env.example` | היגיינת ריפו | — |

**העיקרון:** מה שחייב לקרות תמיד נאכף ב-hooks ובהרשאות. מה שצריך תמיד כתוב ב-`CLAUDE.md`.
מה שצריך רק לפעמים יושב ב-skill. כך הקובץ הראשי נשאר קצר, ו-Claude לא מתעלם מכללים
שקבורים בתוכו.

## הקמה בפרויקט חדש

1. מעתיקים את כל התבנית לשורש הריפו.
2. ב-WSL, Linux או Mac מריצים `chmod +x .claude/hooks/*.sh`. ב-Windows נייטיב ה-hooks
   לא ירוצו, כי הם דורשים bash.
3. פותחים סשן. ה-hook של פתיחת הסשן יזהה placeholders, ו-Claude יפעיל את
   `bootstrap-project`. הוא יסרוק את הריפו, יציע את כל הערכים וההגדרות ויחכה לאישור שלך.
4. אחרי האישור מוודאים ש-`bash .claude/hooks/test-hooks.sh` עובר.

## שלוש שכבות הגנה על סודות

| שכבה | מה היא עושה |
|---|---|
| `.gitignore` | סודות לא נכנסים ל-git. **לא** מונע מ-Claude לקרוא אותם |
| `deny` ב-`settings.json` | Claude לא קורא ולא עורך `.env` ומפתחות |
| `guard-bash.sh` | חוסם `git add .env`, push לפרודקשן, force push ו-`--no-verify` |

**אופציונלי, לבחירתך:**
- [gitleaks](https://github.com/gitleaks/gitleaks) כ-pre-commit, לסריקת סודות לפני commit.
- secret scanning ו-push protection ב-GitHub.

## הרגלי עבודה

| הרגל | למה |
|---|---|
| `/clear` בין משימות | קונטקסט נקי. ה-hook מחזיר אוטומטית את מצב הפרויקט |
| Plan mode (Shift+Tab) | Claude חוקר ומתכנן בלי לשנות קבצים |
| `Esc` | עוצר באמצע, כדי לתקן כיוון מוקדם |
| `@path/to/file` | מפנה את Claude לקובץ מדויק |
| צילום מסך לבאגי UI | מדויק יותר מתיאור במילים |
| `/finish` בסוף משימה | gate, review, תיעוד, hand-off, commit ו-push ברצף אחד |
| git worktrees | כמה סשנים במקביל בלי התנגשויות |

## תחזוקה

- **Claude חוזר על טעות?** חסרה שורה ב-`CLAUDE.md` או ב-`GOTCHAS.md`.
- **Claude מתעלם מכלל?** הכלל ארוך מדי, עמום או קבור. אם הוא קריטי, הופכים אותו ל-hook.
- **ניקוי קבוע:** כל שורה ב-`CLAUDE.md` עולה קונטקסט בכל סשן.
- **שימוש חוזר:** אפשר לשמור את התבנית כ-GitHub template repository ולפתוח ממנה פרויקטים בלחיצה.
